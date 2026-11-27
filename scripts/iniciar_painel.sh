#!/usr/bin/env bash
set -uo pipefail
cd -- "$(dirname -- "$0")/.." || exit 1
echo "Bancada da válvula — digite a senha do Raspberry se for solicitada."
echo "Mantenha este terminal aberto enquanto usa o painel."
sudo --preserve-env=DISPLAY,WAYLAND_DISPLAY,XDG_RUNTIME_DIR,XAUTHORITY ./run.sh --open-browser
status=$?
echo
echo "Programa encerrado (código $status). Pressione Enter para fechar."
read -r
exit "$status"
