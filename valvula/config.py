import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


class Invalid(ValueError):
    pass


def number(value, low, high, name):
    if type(value) not in (int, float) or not low <= value <= high:
        raise Invalid(f"{name} deve ser um número entre {low:g} e {high:g}.")
    return float(value)


def estimated(max_voltage, percent):
    return max_voltage * percent / 100


@dataclass(frozen=True)
class Calibration:
    max_voltage: float = 10.0
    frequency: int = 1000
    calibrated_at: str | None = None

    @classmethod
    def load(cls, path: Path):
        if not path.exists():
            return cls()
        try:
            cfg = cls(**json.loads(path.read_text(encoding="utf-8")))
            number(cfg.max_voltage, 0.1, 10, "Tensão máxima")
            if type(cfg.frequency) is not int or not 1 <= cfg.frequency <= 100000:
                raise ValueError("frequência inválida")
            if cfg.calibrated_at is not None:
                datetime.fromisoformat(cfg.calibrated_at)
            return cfg
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Configuração inválida em {path}: {exc}") from exc

    def calibrate(self, path, value):
        cfg = Calibration(
            number(value, 0.1, 10, "Tensão máxima"), self.frequency, datetime.now(UTC).isoformat()
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
        try:
            temporary.write_text(json.dumps(asdict(cfg), indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return cfg
