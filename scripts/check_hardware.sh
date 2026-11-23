#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
command -v pinctrl >/dev/null || { echo "Instale raspi-utils (pinctrl)." >&2; exit 1; }
echo "Função atual do pino:"
pinctrl get 18
shopt -s nullglob
chips=(/sys/class/pwm/pwmchip*)
(( ${#chips[@]} )) || { echo "Nenhum pwmchip. Confira o overlay e reinicie." >&2; exit 1; }
for chip in "${chips[@]}"; do
  echo "$chip — $(cat "$chip/npwm") canais — $(readlink -f "$chip/device/of_node")"
done
python3 - <<'PY'
import sys
from valvula.hardware import detect_pwm
try:
    chip = detect_pwm()
    print(f"GPIO18 confirmado em {chip}/pwm2 (PWM0_CHAN2).")
except Exception as exc:
    sys.exit(f"Verificação do PWM falhou: {exc}")
PY
