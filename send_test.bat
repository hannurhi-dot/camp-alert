@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo [테스트 알림 발송 - 폰 ntfy 앱에 알림이 오는지 확인하세요]
python camp_check.py --test
echo.
pause
