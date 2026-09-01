@echo off
chcp 65001 >nul
set TASK=생림캠핑감시
schtasks /Delete /F /TN "%TASK%"
if %ERRORLEVEL%==0 (echo [완료] 감시 작업을 삭제했습니다.) else (echo [안내] 등록된 작업이 없거나 삭제에 실패했습니다.)
echo.
pause
