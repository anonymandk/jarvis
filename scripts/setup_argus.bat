@echo off
setlocal
cd /d "%~dp0.."
python scripts\setup_argus.py
if errorlevel 1 (
  echo.
  echo ARGUS setup failed. Read the message above and try again.
  pause
  exit /b 1
)
echo.
echo Add your GEMINI_API_KEY to .env, then run:
echo .venv\Scripts\activate
echo argus
pause
