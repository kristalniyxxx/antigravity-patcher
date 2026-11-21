import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCHER = ROOT / "antigravity_patcher.py"
TASK_NAME = "AntigravityWatchdog"


def run_patcher(*args):
    return subprocess.run([sys.executable, str(PATCHER), *args]).returncode


def is_running(name):
    out = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH"],
        capture_output=True, text=True,
    )
    return name.lower() in out.stdout.lower()


def ask(question):
    try:
        answer = input(f"{question} [y/N]: ")
    except (EOFError, OSError):
        return False
    return answer.strip().lower() in ("y", "yes", "д", "да")


def close_antigravity():
    if not is_running("Antigravity.exe"):
        return True
    print("Antigravity сейчас запущен, для патча его нужно закрыть.")
    if not ask("Закрыть Antigravity?"):
        print("Закрой Antigravity сам и запусти start.bat ещё раз.")
        return False
    for name in ("Antigravity.exe", "language_server.exe"):
        subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True)
    for _ in range(20):
        if not is_running("Antigravity.exe"):
            return True
        time.sleep(0.5)
    print("Antigravity не закрылся. Закрой его вручную и повтори.")
    return False


def watchdog_ok():
    r = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/XML"],
        capture_output=True, text=True, errors="replace",
    )
    if r.returncode != 0:
        return False
    xml = r.stdout.lower()
    return "pythonw.exe" in xml and str(PATCHER).lower() in xml


def main():
    if os.name != "nt":
        print("Antigravity Desktop патчится только на Windows.")
        print("На macOS и Linux патчер не нужен и не работает — см. README.md.")
        return 1

    if sys.version_info < (3, 8):
        print(f"Нужен Python 3.8 или новее, сейчас {sys.version.split()[0]}.")
        return 1

    port = next((a for a in sys.argv[1:] if a.isdigit()), None)

    if not close_antigravity():
        return 1

    print("== Патч ==")
    if run_patcher("patch") != 0:
        return 1

    print()
    print("== Watchdog ==")
    if watchdog_ok():
        print("Задача watchdog уже стоит, переустановка не нужна.")
    else:
        print("Ставлю задачу watchdog: она перепатчит Antigravity после обновлений.")
        run_patcher("watchdog-install")

    print()
    print("== Запуск ==")
    return run_patcher("launch", *([port] if port else []))


if __name__ == "__main__":
    code = main()
    sys.exit(code or 0)
