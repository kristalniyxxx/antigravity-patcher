@echo off
chcp 65001 >nul 2>&1
python "%~dp0antigravity_patcher.py" patch+launch %*
if not "%errorlevel%"=="0" pause
