import builtins

import pytest

from valvula.control import Bench
from valvula.hardware import MockHardware
from valvula.web import create_app


@pytest.fixture
def api(tmp_path):
    bench = Bench(MockHardware(), tmp_path / "cfg.json")
    return create_app(bench).test_client(), bench


def test_full_flow(api):
    client, _ = api
    assert "Teste da válvula proporcional" in client.get("/").text
    for asset in ["painel.js", "painel.css"]:
        assert client.get("/static/" + asset).status_code == 200
    assert client.get("/api/state").json["mock"]
    data = client.post("/api/heartbeat", json={"client": "A"}).json
    client.post("/api/calibration", json={"max_voltage": 8.7})
    data = client.post(
        "/api/apply", json={"client": "A", "percent": 50, "epoch": data["epoch"]}
    ).json
    assert data["volts"] == pytest.approx(4.35)
    assert client.post("/api/stop", json={}).json["phase"] == "Parando"


@pytest.mark.parametrize(
    "data",
    [
        "null",
        "[]",
        "{",
        '{"percent":NaN,"client":"A","epoch":"A"}',
        '{"percent":Infinity,"client":"A","epoch":"A"}',
        '{"percent":"50","client":"A","epoch":"A"}',
        '{"percent":true,"client":"A","epoch":"A"}',
    ],
)
def test_invalid_json(api, data):
    client, bench = api
    assert client.post("/api/apply", data=data, content_type="application/json").status_code == 400
    assert bench.phase == "Desabilitado"


def test_bad_http_requests(api):
    client, bench = api
    assert client.post("/api/apply", data="percent=50").status_code == 415
    assert client.get("/api/apply").status_code == 405
    assert client.post("/api/calibration", json={"max_voltage": 11}).status_code == 400
    assert client.get("/api/state", headers={"Host": "external.test"}).status_code == 400
    assert bench.percent == 0


def test_mock_has_no_gpio_dependency(tmp_path, monkeypatch):
    original = builtins.__import__

    def guard(name, *args, **kwargs):
        assert name.split(".")[0] not in {"gpiod", "gpiozero", "lgpio", "RPi"}
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    bench = Bench(MockHardware(), tmp_path / "cfg.json")
    bench.heartbeat("A")
    bench.apply(30, "A", bench.epoch)
    bench.stop("teste")


def test_exception_in_request_starts_stop(api, monkeypatch):
    client, bench = api
    bench.heartbeat("A")
    bench.apply(25, "A", bench.epoch)

    def broken(value):
        raise OSError("arquivo inacessível")

    monkeypatch.setattr(bench, "calibrate", broken)
    assert client.post("/api/calibration", json={"max_voltage": 8}).status_code == 500
    assert bench.phase == "Parando" and bench.percent == 0 and bench.fault
