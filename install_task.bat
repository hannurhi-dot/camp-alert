@echo off
chcp 65001 >nul
REM ── 생림오토캠핑장 빈자리 감시: 5분마다 실행되는 작업 등록 ──
set TASK=생림캠핑감시
set HERE=%~dp0

schtasks /Create /F /TN "%TASK%" ^
  /TR "wscript.exe \"%HERE%run_silent.vbs\"" ^
  /SC MINUTE /MO 5 ^
  /RL LIMITED

if %ERRORLEVEL%==0 (
  echo.
  echo [완료] "%TASK%" 작업이 등록되었습니다. 5분마다 자동 실행됩니다.
  echo  - 지금 바로 한 번 실행해 봅니다...
  schtasks /Run /TN "%TASK%" >nul
  echo  - 로그: %HERE%camp_check.log
) else (
  echo [실패] 작업 등록에 실패했습니다. 이 창을 관리자 권한으로 다시 실행해 보세요.
)
echo.
pause
