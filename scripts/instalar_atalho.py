"""Instala um atalho de área de trabalho para a bancada no Raspberry Pi."""

import os
import subprocess
from pathlib import Path


def main():
    project = Path(__file__).resolve().parents[1]
    desktop = Path.home() / "Desktop"
    try:
        result = subprocess.run(
            ["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            desktop = Path(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        pass
    if not desktop.is_dir() or desktop == Path.home():
        raise SystemExit("Área de trabalho não encontrada. Confira as configurações do usuário.")
    target = desktop / "Bancada Valvula.desktop"
    if target.exists():
        raise SystemExit(f"O atalho já existe: {target}. Remova-o manualmente para recriá-lo.")
    command = str(project / "scripts" / "iniciar_painel.sh")
    # Desktop Entry Exec has its own quoting rules, independent of the shell.
    quoted = (
        command.replace("%", "%%")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", r"\`")
        .replace("$", "\\$")
    )
    contents = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Bancada da válvula\n"
        "Comment=Iniciar o painel da bancada\n"
        f'Exec="{quoted}"\n'
        "Icon=applications-engineering\n"
        "Terminal=true\n"
        "Categories=Utility;\n"
    )
    with target.open("x", encoding="utf-8") as output:
        output.write(contents)
    os.chmod(target, 0o755)
    print(f"Atalho criado: {target}")


if __name__ == "__main__":
    main()
