# Версионирование

Проект использует семантическое версионирование (SemVer 2.0.0).

Формат: `vMAJOR.MINOR.PATCH`

- **MAJOR** — несовместимые изменения (другой формат запуска, удалён функционал)
- **MINOR** — новая функциональность, обратно совместимая
- **PATCH** — багфиксы без новой функциональности

## Релизы

### v1.0.0 — 2026-11-21

Первый релиз.

- Патч бинарников Antigravity Desktop (`ineligible` → `inexigible`, `https_proxy` → `AG_LS_PROXY`)
- Команды: `scan`, `patch`, `unpatch`, `dry-run`, `launch`, `patch+launch`
- Watchdog: автопатч после обновлений через планировщик Windows
- Команды watchdog: `watchdog`, `watchdog-install`, `watchdog-uninstall`, `watchdog-status`, `watchdog-log`
- Атомарная запись через temp-файл + `os.replace()`
- Бэкапы `.bak` перед первым патчем
- SHA-256 верификация после записи
