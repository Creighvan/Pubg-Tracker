@echo off
REM PUBG Clan Tracker Discord Bot - auto-restart supervisor
REM See README.md > "Auto-Restart on Windows" for what this does and how to use it.

cd /d "%~dp0"

:loop
echo [%date% %time%] Starting PUBG Clan Tracker bot... >> bot_supervisor.log
python -u bot.py >> bot_output.log 2>&1
echo [%date% %time%] Bot exited (code %ERRORLEVEL%^) - restarting in 10 seconds... >> bot_supervisor.log
timeout /t 10 /nobreak >nul
goto loop
