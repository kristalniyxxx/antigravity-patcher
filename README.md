# antigravity-patcher

Патчер для Google Antigravity на Windows. Нужен там, где Antigravity при входе пишет
«not eligible… not currently available in your location» — и десктопное приложение, и
консольный `agy`.

Что делает:

- меняет в бинарниках строку проверки региона (`ineligible` → `inexigible`), после чего
  вход проходит;
- меняет в language server `https_proxy` на `AG_LS_PROXY`, чтобы сервер не подхватывал
  системный прокси и ходил туда, куда скажешь ты (или напрямую через VPN);
- ставит watchdog — задачу в планировщике Windows, которая раз в 5 минут и при входе в
  систему проверяет, не обновился ли Antigravity, и перепатчивает его. Antigravity
  обновляется сам и каждый раз приносит чистый бинарник, без watchdog патч слетает.

Перед первым патчем рядом с каждым файлом кладётся бэкап `*.bak`, запись идёт через
временный файл, после записи сверяется SHA-256. Откатить всё — `unpatch`.

## Запуск

### Windows — одна кнопка

1. Нужен Python 3.8+. Если его нет: https://www.python.org/downloads/ (при установке
   отметить «Add python.exe to PATH») или в терминале `winget install Python.Python.3.12`.
2. Нужен работающий VPN (или локальный прокси) — патч снимает только проверку региона в
   самом приложении, трафик всё равно должен уходить не из РФ.
3. Скачать репозиторий (`git clone` или zip с GitHub) в постоянную папку — watchdog
   запоминает путь к скрипту, поэтому из «Загрузок» потом не переносить.
4. Двойной клик по `start.bat`.

`start.bat` по очереди:

- предложит закрыть Antigravity, если он открыт (с открытым приложением файлы не
  перезаписать);
- пропатчит приложение и `agy.exe`;
- поставит watchdog — Windows один раз спросит права администратора (UAC), это нормально;
  если задача уже стоит, второй раз не спросит;
- запустит Antigravity.

Если VPN работает не в режиме TUN, а как локальный прокси, передай его порт:

    start.bat 7890

Тогда Antigravity и language server пойдут через `http://127.0.0.1:7890`.

### macOS и Ubuntu/Linux

Патчер под них не нужен и не работает: он правит Windows-установку
(`%LOCALAPPDATA%\Programs\Antigravity`). `start.sh` есть для единообразия и просто
скажет об этом:

    sh start.sh

## Команды по отдельности

Если хочется руками, всё то же самое делает сам `antigravity_patcher.py`:

    python antigravity_patcher.py scan            состояние бинарников, ничего не пишет
    python antigravity_patcher.py dry-run         что будет заменено, без записи
    python antigravity_patcher.py patch           пропатчить
    python antigravity_patcher.py unpatch         откатить (из .bak или обратной заменой)
    python antigravity_patcher.py launch [порт]   запустить Antigravity, с прокси или без
    python antigravity_patcher.py patch+launch [порт]
    python antigravity_patcher.py watchdog-install
    python antigravity_patcher.py watchdog-uninstall
    python antigravity_patcher.py watchdog-status
    python antigravity_patcher.py watchdog-log

`scan`, `dry-run`, `patch`, `unpatch` принимают вторым аргументом путь к установке, если
Antigravity стоит не в стандартной папке. `patch_and_launch.cmd` — старый ярлык на
`patch+launch`, оставлен для тех, у кого он уже прописан.

## Если что-то не так

- **«not eligible… in your location» после патча** — Antigravity успел обновиться.
  Закрыть его и запустить `start.bat` ещё раз (или подождать 5 минут, watchdog сделает
  это сам, когда приложение будет закрыто).
- **`proxyconnect tcp: dial tcp 127.0.0.1:<порт>: … actively refused`** — где-то
  осталась переменная `AG_LS_PROXY` (или `HTTPS_PROXY`) на прокси, который больше не
  работает. Чаще всего это следы другого патчера. Проверить:
  `Get-ItemProperty HKCU:\Environment` в PowerShell, лишнюю переменную удалить, Antigravity
  перезапустить полностью.
- **Файл «занят»** — открыт Antigravity или идёт `agy`. Закрыть и повторить.
- Лог watchdog — `watchdog.log` рядом со скриптом (`watchdog-log` показывает хвост).

## Как устроено

Всё в одном файле `antigravity_patcher.py`, внешних зависимостей нет.

- `find_targets` собирает список файлов для патча: `resources\bin\language_server*.exe` и
  бинарники расширения в папке установки, `%USERPROFILE%\.gemini\bin` и консольный
  `%LOCALAPPDATA%\agy\bin\agy.exe`.
- `patch` читает каждый файл целиком, делает побайтовую замену строк из `PATCHES` (длины
  совпадают, поэтому смещения внутри exe не едут), кладёт `.bak`, пишет через временный
  файл и `os.replace`, печатает хеши до и после.
- `watchdog_check` — то, что запускает планировщик: если в каком-то файле снова есть
  исходная строка и Antigravity закрыт, вызывает `patch` и пишет итог в `watchdog.log`.
- `task_install` генерирует PowerShell-скрипт регистрации задачи `AntigravityWatchdog`
  (запуск через `pythonw.exe`, без окна консоли) и выполняет его с повышением прав.
- `launch` стартует `Antigravity.exe`; с портом — добавляет `--proxy-server` и
  выставляет `HTTP(S)_PROXY` и `AG_LS_PROXY` только для этого процесса, систему не трогает.

`scripts/bootstrap.py` — то, что зовут `start.bat`/`start.sh`: проверяет ОС и Python,
закрывает Antigravity по согласию, вызывает `patch`, проверяет, стоит ли задача watchdog с
`pythonw.exe` и путём к этому скрипту (если нет — `watchdog-install`), и вызывает `launch`.
