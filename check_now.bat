@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo [현재 상태 확인 - 알림은 보내지 않음]
python camp_check.py --status
echo.
pause
