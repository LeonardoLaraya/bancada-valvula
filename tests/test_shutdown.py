import signal
import sys
import time
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from valvula import __main__ as cli
from valvula.hardware import MockHardware


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_server_signal_runs_full_discharge(monkeypatch, tmp_path, sig):
    hw = MockHardware()
    captured = {}
    original_handlers = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}

    def app(bench):
        captured["bench"] = bench
        return object()

    def handle_request():
        bench = captured["bench"]
        bench.heartbeat("aba")
        bench.apply(60, "aba", bench.epoch)
        captured["sent_at"] = time.monotonic()
        signal.raise_signal(sig)

    server = SimpleNamespace(server_port=5000, handle_request=handle_request)
    monkeypatch.setattr(cli, "make_server", lambda *a, **kw: nullcontext(server))
    monkeypatch.setattr(cli, "create_app", app)
    monkeypatch.setattr(cli, "MockHardware", lambda: hw)
    monkeypatch.setattr(sys, "argv", ["valvula", "--mock", "--config", str(tmp_path / "cfg.json")])
    try:
        cli.main()
    finally:
        for s, handler in original_handlers.items():
            signal.signal(s, handler)
    assert time.monotonic() - captured["sent_at"] >= 1.49
    assert list(hw.commands)[-3:] == [("PWM", 0), ("ENA", False), ("fechar", True)]
    assert any(sig.name in event["message"] for event in captured["bench"].events)
