import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def update(path):
    lines = path.read_text().splitlines()
    section = "[all]"
    found = False
    for line in lines:
        line = line.partition("#")[0].strip()
        if line.startswith("["):
            section = line.lower()
        if re.match(r"^dtoverlay\s*=\s*pwm-2chan(?:\s*,|\s*$)", line):
            if section not in ("[all]", "[pi5]") or "," in line:
                raise ValueError(
                    "Overlay PWM existente com condição ou parâmetros específicos. "
                    "Confira o GPIO18 e a seção ativa antes de prosseguir."
                )
            found = True
    backup = path.with_name(path.name + ".bak-bancada")
    if not found and backup.exists():
        backup = path.with_name(path.name + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    if not backup.exists():
        shutil.copy2(path, backup)
    print(f"Backup: {backup}")
    if found:
        print("Overlay já configurado.")
    else:
        with path.open("a") as stream:
            stream.write("\n[all]\ndtoverlay=pwm-2chan\n")
        print("Overlay pwm-2chan acrescentado.")


if __name__ == "__main__":
    try:
        update(Path(sys.argv[1]))
    except (ValueError, OSError) as exc:
        sys.exit(f"Falha ao configurar o overlay: {exc}")
