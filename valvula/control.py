import logging
import secrets
import threading
import time
from collections import deque
from dataclasses import asdict
from datetime import datetime

from .config import Calibration, estimated, number
from .hardware import MockHardware

log = logging.getLogger(__name__)


class Conflict(Exception):
    pass


class Bench:
    timeout = 5.0
    discharge = 1.5

    def __init__(self, hardware, path, clock=time.monotonic):
        self.hw = hardware
        self.path = path
        self.config = Calibration.load(path)
        self.clock = clock
        self.lock = threading.RLock()
        self.save_lock = threading.Lock()
        self.stop_intent = threading.Event()
        self.closing = threading.Event()
        self.phase = "Desabilitado"
        self.percent = 0.0
        self.owner = None
        self.beats = {}
        self.epoch = secrets.token_hex(16)
        self.instance = secrets.token_hex(16)
        self.deadline = None
        self.fault = False
        self.events = deque(maxlen=18)
        self.revision = 0
        self.hw.initialize(self.config.frequency)
        self.record("Inicialização com ENA baixo e PWM em 0%.")

    def record(self, message):
        self.revision += 1
        self.events.appendleft(
            {"time": datetime.now().astimezone().isoformat(timespec="seconds"), "message": message}
        )
        log.info("%s", message)

    def finish_stop(self):
        try:
            self.hw.enable(False)
        except Exception as exc:
            log.exception("Erro de escrita no ENA")
            self.fault = True
            self.record(f"Falha ao baixar ENA: {exc}. Verifique a alimentação.")
        self.deadline = None
        self.phase = "Erro" if self.fault else "Desabilitado"
        self.record(self.phase)

    def begin_stop(self, reason, fault=False):
        # Caller holds lock. Rotate even when idle to reject late Apply packets.
        self.epoch = secrets.token_hex(16)
        self.beats.clear()
        self.owner = None
        self.fault |= fault
        self.record(reason)
        if self.deadline is not None:
            return
        try:
            self.hw.duty(0)
            self.percent = 0.0
        except Exception as exc:
            log.exception("Erro de escrita no PWM")
            self.fault = True
            self.percent = None
            self.record(f"Falha ao zerar PWM: {exc}. Desabilitando ENA imediatamente.")
            self.finish_stop()
            return
        self.phase = "Parando"
        self.deadline = self.clock() + self.discharge

    def stop(self, reason, fault=False):
        self.stop_intent.set()
        with self.lock:
            try:
                if not self.closing.is_set():
                    self.begin_stop(reason, fault)
            finally:
                self.stop_intent.clear()

    def tick(self, now=None):
        with self.lock:
            if now is None:
                now = self.clock()
            if self.owner and now - self.beats[self.owner] > self.timeout:
                self.begin_stop("Watchdog: mais de 5 s sem heartbeat da aba de controle.")
            if self.deadline is not None and now >= self.deadline:
                self.finish_stop()

    def heartbeat(self, client):
        with self.lock:
            now = self.clock()
            self.tick(now)  # A late heartbeat must never revive an expired lease.
            self.beats = {k: t for k, t in self.beats.items() if now - t <= self.timeout}
            self.beats[client] = now

    def apply(self, value, client, epoch):
        value = number(value, 0, 100, "Percentual")
        with self.lock:
            self.tick()
            if (
                self.closing.is_set()
                or self.stop_intent.is_set()
                or self.fault
                or self.phase == "Parando"
                or epoch != self.epoch
            ):
                raise Conflict("Comando vencido ou saída bloqueada. Confira o estado.")
            if client not in self.beats or self.clock() - self.beats[client] > self.timeout:
                raise Conflict("Aguardando heartbeat recente desta aba.")
            if self.owner and client != self.owner:
                raise Conflict("Outra aba controla a saída. Use PARAR E ZERAR para assumir.")
            try:
                if self.owner is None:
                    self.hw.duty(0)
                    self.hw.enable(True)
                if self.stop_intent.is_set() or self.closing.is_set():
                    raise Conflict("Parada solicitada.")
                self.hw.duty(value)
            except Conflict:
                raise
            except Exception as exc:
                self.begin_stop(f"Falha ao aplicar: {exc}", fault=True)
                raise Conflict("Falha de hardware. Confira os eventos.") from exc
            self.percent = value
            self.phase = "Habilitado"
            self.owner = client
            self.epoch = secrets.token_hex(16)
            self.record(f"Aplicado {value:g}%.")

    def calibrate(self, value):
        with self.save_lock:
            config = self.config.calibrate(self.path, value)
            with self.lock:
                self.config = config
                self.record(f"Calibração salva: {config.max_voltage:g} V.")

    def snapshot(self):
        with self.lock:
            volts = (
                None if self.percent is None else estimated(self.config.max_voltage, self.percent)
            )
            return {
                "phase": self.phase,
                "percent": self.percent,
                "volts": volts,
                "config": asdict(self.config),
                "mock": isinstance(self.hw, MockHardware),
                "events": list(self.events),
                "revision": self.revision,
                "epoch": self.epoch,
                "instance": self.instance,
            }

    def supervise(self):
        while not self.closing.wait(0.05):
            try:
                self.tick()
            except Exception as exc:
                log.exception("Erro no supervisor")
                self.stop(f"Falha no supervisor: {exc}", fault=True)

    def shutdown(self, reason):
        self.closing.set()
        with self.lock:
            self.begin_stop(reason)
            deadline = self.deadline
        if deadline is not None:
            time.sleep(max(0, deadline - self.clock()))
        with self.lock:
            try:
                if self.deadline is not None:
                    self.finish_stop()
            finally:
                self.hw.close()
