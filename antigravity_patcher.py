import sys
import os
import shutil
import hashlib
import tempfile
import subprocess
import glob
import io

if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Antigravity")

PATCHES = [
    (b"ineligible", b"inexigible"),
    (b"https_proxy", b"AG_LS_PROXY"),
]

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchdog.log")
TASK_NAME = "AntigravityWatchdog"


def log_msg(msg):
    import datetime
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def find_targets(install_root):
    res_bin = os.path.join(install_root, "resources", "bin")
    ext_bin = os.path.join(install_root, "resources", "app", "extensions", "antigravity", "bin")
    targets = []
    fixed = [
        os.path.join(install_root, "agy.exe"),
        os.path.join(res_bin, "language_server.exe"),
        os.path.join(ext_bin, "language_server_windows_x64.exe"),
        os.path.join(ext_bin, "language_server.exe"),
    ]
    for p in fixed:
        if os.path.isfile(p):
            targets.append(p)
    for d in [res_bin, ext_bin]:
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            full = os.path.join(d, name)
            if name.startswith("language_server") and name.endswith(".exe") and os.path.isfile(full) and full not in targets:
                targets.append(full)
    gemini_bin = os.path.join(os.environ.get("USERPROFILE", ""), ".gemini", "bin")
    for name in ["agy.exe", "language_server.exe"]:
        p = os.path.join(gemini_bin, name)
        if os.path.isfile(p) and p not in targets:
            targets.append(p)
    return targets


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def replace_all(data, old, new):
    if len(old) != len(new):
        raise ValueError(f"длины не совпадают: {len(old)} != {len(new)}")
    count = 0
    i = 0
    result = bytearray(data)
    while i + len(old) <= len(result):
        if result[i:i + len(old)] == old:
            result[i:i + len(new)] = new
            count += 1
            i += len(old)
        else:
            i += 1
    return bytes(result), count


def write_atomic(target, data):
    d = os.path.dirname(target)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        os.write(fd, data)
        os.close(fd)
        fd = -1
        os.replace(tmp, target)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def is_process_running(name):
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        return name.lower() in out.stdout.lower()
    except Exception:
        return False


def kill_process(name):
    subprocess.run(
        ["taskkill", "/F", "/IM", name],
        capture_output=True, timeout=10
    )


def scan(install_root):
    targets = find_targets(install_root)
    if not targets:
        print(f"  Бинарники не найдены в {install_root}")
        return
    for t in targets:
        name = os.path.relpath(t, install_root)
        data = open(t, "rb").read()
        size_mb = len(data) / (1024 * 1024)
        states = []
        for old, new in PATCHES:
            has_old = old in data
            has_new = new in data
            if has_new and not has_old:
                states.append(f"{old.decode()} → уже заменено на {new.decode()}")
            elif has_old:
                c = data.count(old)
                states.append(f"{old.decode()} → найдено {c} раз, можно заменить")
            else:
                states.append(f"{old.decode()} → не найдено (другая версия?)")
        print(f"  {name} ({size_mb:.1f} МБ)")
        for s in states:
            print(f"    {s}")


def patch(install_root, dry_run=False):
    targets = find_targets(install_root)
    if not targets:
        print("Бинарники не найдены.")
        return False

    total_patched = 0
    for t in targets:
        name = os.path.relpath(t, install_root)
        data = open(t, "rb").read()
        modified = data
        file_changed = False
        for old, new in PATCHES:
            modified, count = replace_all(modified, old, new)
            if count > 0:
                file_changed = True
                print(f"  {name}: {old.decode()} → {new.decode()} ({count} замен)")

        if not file_changed:
            has_patched = all(new in data for _, new in PATCHES)
            if has_patched:
                print(f"  {name}: уже пропатчен")
            else:
                print(f"  {name}: сигнатура не найдена — пропущен")
            continue

        if dry_run:
            print(f"  {name}: будет записано (dry-run)")
            total_patched += 1
            continue

        backup = t + ".bak"
        if not os.path.exists(backup):
            shutil.copy2(t, backup)
            print(f"  бэкап: {os.path.basename(backup)}")

        old_hash = sha256(t)
        write_atomic(t, modified)
        new_hash = sha256(t)
        print(f"  {name}: записано")
        print(f"    было:  {old_hash}")
        print(f"    стало: {new_hash}")
        total_patched += 1

    return total_patched > 0


def unpatch(install_root):
    targets = find_targets(install_root)
    restored = 0
    for t in targets:
        backup = t + ".bak"
        name = os.path.relpath(t, install_root)
        if os.path.exists(backup):
            write_atomic(t, open(backup, "rb").read())
            os.remove(backup)
            print(f"  {name}: восстановлен из бэкапа")
            restored += 1
            continue
        data = open(t, "rb").read()
        modified = data
        file_changed = False
        for old, new in PATCHES:
            modified, count = replace_all(modified, new, old)
            if count > 0:
                file_changed = True
        if file_changed:
            write_atomic(t, modified)
            print(f"  {name}: обратная замена (бэкапа не было)")
            restored += 1
        else:
            print(f"  {name}: не пропатчен, пропущен")
    if restored == 0:
        print("  Нечего откатывать.")


def launch(install_root, proxy_port=None):
    exe = os.path.join(install_root, "Antigravity.exe")
    if not os.path.isfile(exe):
        print(f"Antigravity.exe не найден в {install_root}")
        return
    if is_process_running("Antigravity.exe"):
        print("Antigravity уже запущен. Закрой его и попробуй снова.")
        return

    env = os.environ.copy()
    args = [exe]
    if proxy_port:
        proxy = f"http://127.0.0.1:{proxy_port}"
        args += [f"--proxy-server={proxy}", "--proxy-bypass-list=localhost;127.0.0.1;[::1]"]
        env["HTTP_PROXY"] = proxy
        env["HTTPS_PROXY"] = proxy
        env["AG_LS_PROXY"] = proxy
        no_proxy = set(filter(None, env.get("NO_PROXY", "").split(",")))
        no_proxy.update(["localhost", "127.0.0.1", "::1"])
        env["NO_PROXY"] = ",".join(no_proxy)
        print(f"Запуск через прокси {proxy}")
    else:
        print("Запуск без прокси (VPN должен быть включён)")

    proc = subprocess.Popen(args, env=env, cwd=install_root)
    print(f"Antigravity запущен (PID {proc.pid})")


def needs_patch(install_root):
    targets = find_targets(install_root)
    for t in targets:
        data = open(t, "rb").read()
        for old, new in PATCHES:
            if old in data:
                return True
    return False


def watchdog_check(install_root):
    if not os.path.isdir(install_root):
        return
    if not needs_patch(install_root):
        return

    log_msg("Обнаружен непропатченный бинарник — перепатчиваю")

    ls_name = "language_server.exe"
    if is_process_running(ls_name):
        log_msg(f"Завершаю {ls_name}")
        kill_process(ls_name)
        import time; time.sleep(2)

    if is_process_running("Antigravity.exe"):
        log_msg("Antigravity.exe запущен — пропускаю (патч возможен только с закрытым приложением)")
        return

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = patch(install_root)
    finally:
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

    if result:
        log_msg("Перепатчено:\n" + output.strip())
    else:
        log_msg("Патч не применился:\n" + output.strip())


def task_install():
    script = os.path.abspath(__file__)
    python = sys.executable

    work_dir = os.path.dirname(script)
    ps_content = (
        f"$action = New-ScheduledTaskAction -Execute '{python}' "
        f"-Argument '\"{script}\" watchdog' -WorkingDirectory '{work_dir}'\n"
        f"$trigger1 = New-ScheduledTaskTrigger -Once -At (Get-Date) "
        f"-RepetitionInterval (New-TimeSpan -Minutes 5)\n"
        f"$trigger2 = New-ScheduledTaskTrigger -AtLogOn\n"
        f"$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
        f"-DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2) "
        f"-MultipleInstances IgnoreNew\n"
        f"Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $action "
        f"-Trigger $trigger1,$trigger2 -Settings $settings -Force | Out-Null\n"
    )
    ps_path = os.path.join(tempfile.gettempdir(), "ag_watchdog_install.ps1")
    with open(ps_path, "w", encoding="utf-8") as f:
        f.write(ps_content)

    print("Для создания задачи нужны права администратора.")
    print("Откроется окно UAC...")

    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Start-Process powershell -Verb RunAs -Wait "
         f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','{ps_path}'"],
        capture_output=True, text=True, timeout=60
    )

    try:
        os.remove(ps_path)
    except Exception:
        pass

    check = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True, text=True
    )
    if check.returncode == 0:
        print(f"Задача '{TASK_NAME}' создана в планировщике.")
        print("  Запускается каждые 5 минут и при входе в систему.")
        print(f"  Лог: {LOG_FILE}")
    else:
        print("Задача не создана. Попробуй запустить от имени администратора:")
        print(f"  powershell -File \"{ps_path}\"")
        sys.exit(1)


def task_uninstall():
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Start-Process powershell -Verb RunAs -Wait "
         f"-ArgumentList '-NoProfile','-Command',"
         f"'Unregister-ScheduledTask -TaskName {TASK_NAME} -Confirm:$false'"],
        capture_output=True, text=True, timeout=60
    )
    check = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True, text=True
    )
    if check.returncode != 0:
        print(f"Задача '{TASK_NAME}' удалена из планировщика.")
    else:
        print("Не удалось удалить задачу. Попробуй от имени администратора.")


def task_status():
    r = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print(r.stdout)
    else:
        print(f"Задача '{TASK_NAME}' не найдена в планировщике.")


def usage():
    print("""antigravity_patcher.py — свой патчер Antigravity Desktop

Использование:
  python antigravity_patcher.py scan [путь]       — показать состояние бинарников
  python antigravity_patcher.py patch [путь]       — пропатчить (замена ineligible + https_proxy)
  python antigravity_patcher.py dry-run [путь]     — показать что будет заменено, без записи
  python antigravity_patcher.py unpatch [путь]     — откатить патч (из бэкапа или обратной заменой)
  python antigravity_patcher.py launch [порт]      — запустить Antigravity через прокси
  python antigravity_patcher.py launch             — запустить Antigravity без прокси (для VPN)
  python antigravity_patcher.py patch+launch [порт] — пропатчить и сразу запустить

Watchdog (автопатч после обновлений):
  python antigravity_patcher.py watchdog           — одна проверка: перепатчить если нужно
  python antigravity_patcher.py watchdog-install   — создать задачу в планировщике Windows
  python antigravity_patcher.py watchdog-uninstall — удалить задачу из планировщика
  python antigravity_patcher.py watchdog-status    — показать состояние задачи
  python antigravity_patcher.py watchdog-log       — показать последние записи лога

По умолчанию ищет установку в %LOCALAPPDATA%\\Programs\\Antigravity.
Можно указать другой путь вторым аргументом для scan/patch/unpatch.
""")


def resolve_install(arg=None):
    path = arg or INSTALL_DIR
    if not os.path.isdir(path):
        print(f"Папка не найдена: {path}")
        sys.exit(1)
    return path


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(0)

    cmd = sys.argv[1].lower()
    extra = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd == "scan":
        install = resolve_install(extra)
        print(f"Сканирование {install}:")
        scan(install)

    elif cmd == "dry-run":
        install = resolve_install(extra)
        print(f"Проверка (dry-run) {install}:")
        patch(install, dry_run=True)

    elif cmd == "patch":
        install = resolve_install(extra)
        ls_name = "language_server.exe"
        ag_name = "Antigravity.exe"
        if is_process_running(ls_name):
            print(f"{ls_name} запущен — завершаю...")
            kill_process(ls_name)
            import time; time.sleep(1)
        if is_process_running(ag_name):
            print(f"{ag_name} запущен. Закрой Antigravity и попробуй снова.")
            sys.exit(1)
        print(f"Патч {install}:")
        if patch(install):
            print("Готово.")
        else:
            print("Ничего не пропатчено.")

    elif cmd == "unpatch":
        install = resolve_install(extra)
        ls_name = "language_server.exe"
        ag_name = "Antigravity.exe"
        if is_process_running(ls_name):
            kill_process(ls_name)
            import time; time.sleep(1)
        if is_process_running(ag_name):
            print(f"{ag_name} запущен. Закрой Antigravity и попробуй снова.")
            sys.exit(1)
        print(f"Откат {install}:")
        unpatch(install)

    elif cmd == "launch":
        port = int(extra) if extra and extra.isdigit() else None
        install = resolve_install()
        launch(install, port)

    elif cmd == "patch+launch":
        port = int(extra) if extra and extra.isdigit() else None
        install = resolve_install()
        ls_name = "language_server.exe"
        ag_name = "Antigravity.exe"
        if is_process_running(ag_name):
            print(f"{ag_name} запущен. Закрой Antigravity и попробуй снова.")
            sys.exit(1)
        if is_process_running(ls_name):
            kill_process(ls_name)
            import time; time.sleep(1)
        print(f"Патч {install}:")
        patch(install)
        print()
        launch(install, port)

    elif cmd == "watchdog":
        install = resolve_install(extra)
        watchdog_check(install)

    elif cmd == "watchdog-install":
        task_install()

    elif cmd == "watchdog-uninstall":
        task_uninstall()

    elif cmd == "watchdog-status":
        task_status()

    elif cmd == "watchdog-log":
        if os.path.isfile(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[-30:]:
                print(line, end="")
        else:
            print("Лог пуст (файл не существует).")

    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
