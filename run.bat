@echo off
chcp 65001 > nul
title Telegram Mini App Post Publisher (@Almuraadmin_bot)
echo ========================================================
echo   Telegram Post & Scheduler Mini App ishga tushmoqda...
echo   Bot: @Almuraadmin_bot
echo   Port: 8000
echo ========================================================
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
