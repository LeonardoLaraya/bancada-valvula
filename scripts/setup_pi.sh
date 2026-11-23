#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ ${1:-} == --check ]]; then exec bash check_hardware.sh; fi
if [[ $# != 0 ]]; then echo "Uso: setup_pi.sh [--check]" >&2; exit 2; fi
model=/proc/device-tree/model
config=/boot/firmware/config.txt
[[ -r "$model" ]] && grep -aq '^Raspberry Pi 5 Model ' "$model" || {
  echo "Execute este script no Raspberry Pi 5." >&2; exit 1; }
[[ -f "$config" && -w "$config" ]] || {
  echo "Sem acesso a $config. Confira a montagem de boot e use sudo." >&2; exit 1; }

python3 update_overlay.py "$config"
echo "A ativação do overlay requer reinicialização manual: sudo reboot"
echo "Depois do boot, execute: bash scripts/check_hardware.sh"
