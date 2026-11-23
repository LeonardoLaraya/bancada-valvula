import argparse
import logging
import os
import shutil
import signal
import subprocess
import threading
import webbrowser
from pathlib import Path

from werkzeug.serving import make_server

from .control import Bench
from .hardware import MockHardware, RaspberryPiHardware
from .web import create_app

log = logging.getLogger(__name__)


def open_browser(url):
    browser = shutil.which("chromium") or shutil.which("chromium-browser")
    if browser and hasattr(os, "geteuid") and os.geteuid() == 0:
        user = os.environ.get("SUDO_USER")
        if user and user != "root":
            subprocess.Popen(["runuser", "-u", user, "--", browser, url])
        else:
            log.warning("Abra %s na sessão gráfica do operador.", url)
    elif browser:
        subprocess.Popen([browser, url])
    else:
        webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description="Bancada local EPV2-5031F2")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--config", type=Path, help="Caminho do JSON de calibração")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    reason = "Encerramento normal."
    quit_requested = threading.Event()

    def on_signal(signum, frame):
        nonlocal reason
        reason = f"Encerramento por {signal.Signals(signum).name}."
        quit_requested.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, on_signal)
    path = args.config or Path(__file__).resolve().parents[1] / "data" / (
        "mock.json" if args.mock else "calibracao.json"
    )
    bench = Bench(MockHardware() if args.mock else RaspberryPiHardware(), path)
    try:
        with make_server("127.0.0.1", args.port, create_app(bench), threaded=True) as server:
            server.timeout = 0.1
            guard = threading.Thread(target=bench.supervise, name="watchdog", daemon=True)
            guard.start()
            url = f"http://127.0.0.1:{server.server_port}"
            log.info("%s | %s", "MODO SIMULADO" if args.mock else "Hardware real", url)
            if args.open_browser:
                open_browser(url)
            while not quit_requested.is_set():
                server.handle_request()
    except BaseException as exc:
        reason = f"Encerramento do servidor: {type(exc).__name__} {exc}"
        raise
    finally:
        bench.shutdown(reason)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, ImportError, subprocess.SubprocessError) as exc:
        raise SystemExit(
            f"Falha na bancada: {exc}. Confira a configuração e scripts/check_hardware.sh."
        ) from exc
