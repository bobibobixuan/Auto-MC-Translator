from __future__ import annotations

import importlib
import os
import socket
import sys
import webbrowser
from pathlib import Path
from threading import Thread


def relaunch_in_project_venv() -> None:
    if os.getenv("MC_TRANSLATOR_SKIP_VENV_RELAUNCH") == "1":
        return

    project_root = Path(__file__).resolve().parent
    candidate_paths = [
        project_root / ".venv" / "Scripts" / "python.exe",
        project_root / ".venv" / "bin" / "python",
    ]

    venv_python = next((path for path in candidate_paths if path.exists()), None)
    if venv_python is None:
        return

    current_python = Path(sys.executable).resolve()
    if current_python == venv_python.resolve():
        return

    os.environ["MC_TRANSLATOR_SKIP_VENV_RELAUNCH"] = "1"
    os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])


relaunch_in_project_venv()

uvicorn = importlib.import_module("uvicorn")
app = importlib.import_module("mc_ai_translator.web_ui").app


def find_available_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def build_browser_url(host: str, port: int) -> str:
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{browser_host}:{port}"


if __name__ == "__main__":
    host = os.getenv("MC_TRANSLATOR_HOST", "127.0.0.1")
    preferred_port = int(os.getenv("MC_TRANSLATOR_PORT", "7860"))
    port = find_available_port(host, preferred_port)
    launch_url = build_browser_url(host, port)

    Thread(target=lambda: webbrowser.open(launch_url), daemon=True).start()
    uvicorn.run(app, host=host, port=port, reload=False)