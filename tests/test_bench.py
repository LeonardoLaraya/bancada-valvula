from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from valvula.config import Calibration, Invalid, estimated, number
from valvula.control import Bench, Conflict
from valvula.hardware import MockHardware


@pytest.fixture
def rig(tmp_path):
    now = [100.0]
    hw = MockHardware()
    bench = Bench(hw, tmp_path / "cal.json", clock=lambda: now[0])
    return bench, hw, now


@pytest.mark.parametrize("value", [-0.1, 100.1, True, "50", None, float("nan"), float("inf")])
def test_percent_invalid(value):
    with pytest.raises(Invalid):
        number(value, 0, 100, "Percentual")


@pytest.mark.parametrize("value", [0, 0.09, 10.1, True, "8.7", None, float("nan"), -float("inf")])
def test_calibration_invalid(rig, value):
    bench, _, _ = rig
    with pytest.raises(Invalid):
        bench.calibrate(value)
    assert not bench.path.exists()


def test_boot_apply_stop_order_and_discharge(rig):
    bench, hw, now = rig
    assert list(hw.commands) == [("ENA", False), ("Hz", 1000), ("PWM", 0)]
    assert bench.snapshot()["phase"] == "Desabilitado"
    assert bench.config.calibrated_at is None
    bench.heartbeat("A")
    bench.apply(100, "A", bench.epoch)
    assert list(hw.commands)[-3:] == [("PWM", 0), ("ENA", True), ("PWM", 100)]
    bench.apply(0, "A", bench.epoch)
    assert bench.phase == "Habilitado"
    bench.stop("operador")
    assert hw.commands[-1] == ("PWM", 0)
    assert bench.phase == "Parando"
    now[0] += 1.49
    bench.tick()
    assert hw.commands[-1] == ("PWM", 0)
    now[0] += 0.02
    bench.tick()
    assert hw.commands[-1] == ("ENA", False)
    assert bench.phase == "Desabilitado"


def test_watchdog_owner_only_and_late_heartbeat(rig):
    bench, hw, now = rig
    bench.heartbeat("A")
    bench.apply(50, "A", bench.epoch)
    now[0] += 4
    bench.heartbeat("B")
    with pytest.raises(Conflict):
        bench.apply(80, "B", bench.epoch)
    now[0] += 1.01
    bench.heartbeat("A")
    assert bench.phase == "Parando"
    assert hw.commands[-1] == ("PWM", 0)
    assert "Watchdog" in bench.events[0]["message"]
    now[0] += 1.5
    bench.tick()
    assert hw.commands[-1] == ("ENA", False)


def test_invalidated_commands_and_fresh_heartbeat(rig):
    bench, _, now = rig
    with pytest.raises(Conflict):
        bench.apply(10, "A", bench.epoch)
    bench.heartbeat("A")
    epoch = bench.epoch
    bench.stop("parada")
    now[0] += 2
    bench.tick()
    bench.heartbeat("A")
    with pytest.raises(Conflict):
        bench.apply(50, "A", epoch)
    now[0] += 5.01
    with pytest.raises(Conflict):
        bench.apply(50, "A", bench.epoch)


def test_concurrent_stop_and_apply(rig):
    bench, hw, now = rig
    bench.heartbeat("A")
    epoch = bench.epoch
    go = Event()

    def apply():
        go.wait()
        try:
            bench.apply(75, "A", epoch)
        except Conflict:
            pass

    def stop():
        go.wait()
        bench.stop("concorrência")

    with ThreadPoolExecutor(max_workers=8) as pool:
        tasks = [pool.submit(apply) for _ in range(7)] + [pool.submit(stop)]
        go.set()
        for task in tasks:
            task.result(timeout=2)
    assert bench.percent == 0
    assert hw.commands[-1] == ("PWM", 0)
    now[0] += 1.5
    bench.tick()
    assert hw.commands[-1] == ("ENA", False)


def test_only_calibration_persists(rig):
    import json

    bench, _, _ = rig
    assert estimated(8.7, 50) == pytest.approx(4.35)
    bench.calibrate(8.7)
    bench.heartbeat("A")
    bench.apply(50, "A", bench.epoch)
    assert bench.snapshot()["volts"] == pytest.approx(4.35)
    assert set(json.loads(bench.path.read_text())) == {"calibrated_at", "frequency", "max_voltage"}
    second = Bench(MockHardware(), bench.path)
    assert second.config == bench.config
    assert second.percent == 0 and second.phase == "Desabilitado"
    assert second.epoch != bench.epoch


@pytest.mark.parametrize("volts", [0.1, 10])
def test_calibration_limits(rig, volts):
    bench, _, _ = rig
    bench.calibrate(volts)
    assert Calibration.load(bench.path).max_voltage == volts


def test_io_error_latches_until_restart(rig, monkeypatch):
    bench, hw, now = rig
    duty = hw.duty

    def fail_nonzero(value):
        if value:
            raise OSError("PWM ocupado")
        duty(value)

    monkeypatch.setattr(hw, "duty", fail_nonzero)
    bench.heartbeat("A")
    with pytest.raises(Conflict):
        bench.apply(50, "A", bench.epoch)
    assert hw.commands[-1] == ("PWM", 0)
    now[0] += 1.5
    bench.tick()
    assert bench.phase == "Erro" and hw.commands[-1] == ("ENA", False)
    with pytest.raises(Conflict):
        bench.apply(50, "A", bench.epoch)


def test_zero_write_failure_drops_ena_immediately(rig, monkeypatch):
    bench, hw, _ = rig
    bench.heartbeat("A")
    bench.apply(100, "A", bench.epoch)

    def broken(value):
        raise OSError("PWM inacessível")

    monkeypatch.setattr(hw, "duty", broken)
    bench.stop("operador")
    assert bench.phase == "Erro" and bench.snapshot()["volts"] is None
    assert hw.commands[-1] == ("ENA", False)
