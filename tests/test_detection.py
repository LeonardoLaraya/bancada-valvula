from types import SimpleNamespace

import pytest

from valvula.hardware import detect_pwm


@pytest.fixture
def tree(tmp_path, monkeypatch):
    chips = tmp_path / "pwm"
    correct = chips / "pwmchip17"
    for chip in [correct, chips / "pwmchip2"]:
        node = chip / "device/of_node"
        node.mkdir(parents=True)
        (node / "compatible").write_bytes(b"raspberrypi,rp1-pwm\0")
        (chip / "npwm").write_text("4")
    (tmp_path / "__symbols__").mkdir()
    (tmp_path / "__symbols__/rp1_pwm0").write_bytes(b"/pwm/pwmchip17/device/of_node\0")
    (tmp_path / "model").write_bytes(b"Raspberry Pi 5 Model B Rev 1.0\0")

    def pinctrl(args, **kwargs):
        assert args == ["pinctrl", "get", "18"]
        return SimpleNamespace(stdout="18: a3 pd | lo // GPIO18 = PWM0_CHAN2")

    monkeypatch.setattr("valvula.hardware.subprocess.run", pinctrl)
    return chips, tmp_path, correct


def test_uses_live_node_not_chip_number(tree):
    chips, root, correct = tree
    assert detect_pwm(chips, root) == correct


def test_wrong_mux_rejected(tree, monkeypatch):
    chips, root, _ = tree
    monkeypatch.setattr(
        "valvula.hardware.subprocess.run",
        lambda *a, **kw: SimpleNamespace(stdout="18: ip pd | lo // GPIO18 = input"),
    )
    with pytest.raises(RuntimeError, match="função"):
        detect_pwm(chips, root)


def test_missing_channel_rejected(tree):
    chips, root, correct = tree
    (correct / "npwm").write_text("2")
    with pytest.raises(RuntimeError, match="encontrados 0"):
        detect_pwm(chips, root)
