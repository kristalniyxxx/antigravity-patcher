# Версионирование

Проект использует семантическое версионирование (SemVer 2.0.0).

Формат: `vMAJOR.MINOR.PATCH`

- **MAJOR** — несовместимые изменения (другой формат запуска, удалён функционал)
- **MINOR** — новая функциональность, обратно совместимая
- **PATCH** — багфиксы без новой функциональности

## Релизы

### v1.1.1 — 2026-11-22

- Watchdog больше не завершает language server у открытого Antigravity: сначала проверяет,
  закрыто ли приложение, и только потом патчит

### v1.1.0 — 2026-11-22

- `start.bat` / `start.sh` + `scripts/bootstrap.py`: установка одной кнопкой — патч,
  watchdog, запуск
- Патчится и консольный `agy.exe` (`%LOCALAPPDATA%\agy\bin`)
- Watchdog запускается через `pythonw.exe` без окна консоли; исправлено падение
  скрипта при запуске без консоли
- Занятый файл при патче пропускается с сообщением, а не роняет весь патч
- `patch` сначала проверяет, закрыт ли Antigravity, и только потом завершает language server
- README

### v1.0.0 — 2026-11-21

Первый релиз.

- Патч бинарников Antigravity Desktop (`ineligible` → `inexigible`, `https_proxy` → `AG_LS_PROXY`)
- Команды: `scan`, `patch`, `unpatch`, `dry-run`, `launch`, `patch+launch`
- Watchdog: автопатч после обновлений через планировщик Windows
- Команды watchdog: `watchdog`, `watchdog-install`, `watchdog-uninstall`, `watchdog-status`, `watchdog-log`
- Атомарная запись через temp-файл + `os.replace()`
- Бэкапы `.bak` перед первым патчем
- SHA-256 верификация после записи
