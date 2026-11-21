@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo Python не найден.
    echo Поставь Python 3.8+ с https://www.python.org/downloads/ ^(галочка "Add python.exe to PATH"^)
    echo или командой: winget install Python.Python.3.12
    pause
    exit /b 1
)

%PY% "%~dp0scripts\bootstrap.py" %*
if not "%errorlevel%"=="0" pause
