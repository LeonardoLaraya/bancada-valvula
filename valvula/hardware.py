import logging
import re
import subprocess
import time
from abc import ABC, abstractmethod
from collections import deque
from pathlib import Path

log = logging.getLogger(__name__)


class HardwareController(ABC):
    @abstractmethod
    def initialize(self, frequency): ...

    @abstractmethod
    def enable(self, active): ...

    @abstractmethod
    def duty(self, percent): ...

    @abstractmethod
    def close(self): ...


class MockHardware(HardwareController):
    def __init__(self):
        self.commands = deque(maxlen=256)

    def record(self, key, value):
        self.commands.append((key, value))
        log.info("Simulado | %s %s", key, value)

    def initialize(self, frequency):
        self.enable(False)
        self.record("Hz", frequency)
        self.duty(0)

    def enable(self, active):
        self.record("ENA", active)

    def duty(self, percent):
        self.record("PWM", percent)

    def close(self):
        self.record("fechar", True)


def detect_pwm(root=Path("/sys/class/pwm"), tree=Path("/proc/device-tree")):
    model = (tree / "model").read_bytes().rstrip(b"\0").decode()
    if not model.startswith("Raspberry Pi 5 Model "):
        raise RuntimeError(f"Plataforma incompatível: {model}")
    result = subprocess.run(
        ["pinctrl", "get", "18"], capture_output=True, text=True, check=True, timeout=3
    )
    if not re.search(r"(?im)^\s*18:\s*a3\b[^\n]*\bGPIO18\s*=\s*PWM0_CHAN2\b", result.stdout):
        raise RuntimeError(f"GPIO18 fora da função PWM0_CHAN2: {result.stdout.strip()}")
    # Both RP1 PWM blocks share a compatible string. Match the exact live DT node.
    symbol = (tree / "__symbols__/rp1_pwm0").read_bytes().rstrip(b"\0").decode()
    target = (tree / symbol.lstrip("/")).resolve(strict=True)
    if b"raspberrypi,rp1-pwm" not in (target / "compatible").read_bytes().split(b"\0"):
        raise RuntimeError("rp1_pwm0 não identifica um PWM RP1 compatível.")
    matches = [
        chip
        for chip in root.glob("pwmchip*")
        if (chip / "device/of_node").resolve() == target and int((chip / "npwm").read_text()) > 2
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Esperado um pwmchip do rp1_pwm0 com canal 2; encontrados {len(matches)}."
        )
    return matches[0]


class RaspberryPiHardware(HardwareController):
    def __init__(self):
        self.line = None
        self.chip = None
        self.exported = False

    def initialize(self, frequency):
        import gpiod
        from gpiod.line import Direction, Value

        self.values = Value
        # The gpiochip number also changes between Pi kernels.
        matches = {}
        for path in Path("/dev").glob("gpiochip[0-9]*"):
            with gpiod.Chip(str(path)) as gpio:
                if (
                    gpio.get_info().label == "pinctrl-rp1"
                    and gpio.get_line_info(23).name == "GPIO23"
                ):
                    matches.setdefault(path.stat().st_rdev, path)
        if len(matches) != 1:
            raise RuntimeError("GPIO23 não identificado de forma única no pinctrl-rp1.")
        settings = gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)
        self.line = gpiod.request_lines(
            str(next(iter(matches.values()))), consumer="bancada-ena", config={23: settings}
        )
        try:
            self.chip = detect_pwm()
            self.channel = self.chip / "pwm2"
            # Export must succeed: never take over an existing consumer.
            (self.chip / "export").write_text("2")
            self.exported = True
            deadline = time.monotonic() + 1
            while not (self.channel / "period").exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.period = round(1_000_000_000 / frequency)
            if (self.channel / "enable").read_text().strip() == "1":
                self.write("enable", 0)
            if int((self.channel / "duty_cycle").read_text()):
                self.write("duty_cycle", 0)
            self.write("period", self.period)
            if (self.channel / "polarity").read_text().strip() != "normal":
                self.write("polarity", "normal")
            self.duty(0)
            self.write("enable", 1)
            log.info("GPIO18: %s/pwm2, período %s ns", self.chip, self.period)
        except BaseException:
            self.close()
            raise

    def write(self, attribute, value):
        (self.channel / attribute).write_text(str(value))

    def duty(self, percent):
        self.write("duty_cycle", round(self.period * percent / 100))

    def enable(self, active):
        self.line.set_value(23, self.values.ACTIVE if active else self.values.INACTIVE)

    def close(self):
        try:
            if self.line is not None:
                self.enable(False)
        finally:
            try:
                if self.exported:
                    try:
                        self.write("enable", 0)
                    finally:
                        (self.chip / "unexport").write_text("2")
                        self.exported = False
            finally:
                if self.line is not None:
                    self.line.release()
                    self.line = None
