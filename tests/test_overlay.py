import pytest

from scripts.update_overlay import update


def test_appends_to_active_section_and_preserves_backup(tmp_path):
    config = tmp_path / "config.txt"
    before = "[pi4]\n#dtoverlay=pwm-2chan\n"
    config.write_text(before)
    update(config)
    assert config.read_text() == before + "\n[all]\ndtoverlay=pwm-2chan\n"
    first = config.read_bytes()
    update(config)
    assert config.read_bytes() == first
    assert (tmp_path / "config.txt.bak-bancada").read_text() == before
    assert len(list(tmp_path.iterdir())) == 2


def test_existing_overlay_is_backed_up(tmp_path):
    config = tmp_path / "config.txt"
    config.write_text("[pi5]\ndtoverlay=pwm-2chan # GPIO18\n")
    before = config.read_bytes()
    update(config)
    assert config.read_bytes() == before
    assert (tmp_path / "config.txt.bak-bancada").read_bytes() == before


@pytest.mark.parametrize("setting", ["[pi4]\ndtoverlay=pwm-2chan", "dtoverlay=pwm-2chan,pin=12"])
def test_custom_overlay_is_preserved(tmp_path, setting):
    config = tmp_path / "config.txt"
    config.write_text(setting)
    with pytest.raises(ValueError):
        update(config)
    assert config.read_text() == setting
