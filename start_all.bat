@echo off
REM =====================================================
REM AI COURTROOM SIMULATOR - PROFESSIONAL EDITION
REM =====================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

cls
echo.
echo ======================================================================
echo           AI COURTROOM SIMULATOR - PROFESSIONAL EDITION
echo                      ENHANCED STARTUP SEQUENCE
echo ======================================================================
echo.
echo Features: Authentication, Evidence Management, Analytics, Multi-Case Types
echo Database: SQLite with user management and session tracking
echo AI Models: Enhanced prompts with legal knowledge base
echo.

REM Check if venv exists
if not exist "venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

echo [STEP 1] Checking Enhanced Python Environment...
venv\Scripts\python.exe --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in venv!
    pause
    exit /b 1
)
echo [✓] Python environment ready

echo [STEP 2] Installing/Updating Enhanced Dependencies...
venv\Scripts\pip.exe install -r requirements.txt --quiet
echo [✓] Dependencies updated

echo [STEP 3] Checking Ollama AI Service...
netstat -ano 2>nul | findstr ":11434" >nul 2>&1
if errorlevel 1 (
    echo [!] Ollama not detected - AI will use fallback responses
    echo To enable full AI: run 'ollama serve' in another terminal
    timeout /t 2 /nobreak
) else (
    echo [✓] Ollama AI service detected and ready
)

echo [STEP 4] Initializing Database...
venv\Scripts\python.exe -c "from server import init_database; init_database(); print('Database initialized')"
echo [✓] SQLite database ready

echo [STEP 5] Starting Enhanced Backend Server...
start "Enhanced Backend - AI Courtroom" cmd /k "cd /d "%~dp0" && venv\Scripts\python.exe server.py"

timeout /t 4 /nobreak

echo [STEP 6] Starting Professional Frontend...
start "Professional Frontend - AI Courtroom" cmd /k "cd /d "%~dp0" && venv\Scripts\python.exe -m streamlit run app.py"

echo.
echo ======================================================================
echo                    PROFESSIONAL EDITION READY!
echo ======================================================================
echo.
echo 🌐 URLS:
echo    Frontend (UI):     http://localhost:8501
echo    Backend (API):     http://127.0.0.1:8000
echo    API Docs:          http://127.0.0.1:8000/docs
echo    Health Check:      http://127.0.0.1:8000/health
echo.
echo 🚀 NEW FEATURES:
echo    ✅ User Authentication & Registration
echo    ✅ Multiple Case Types (Criminal, Civil, Family, Corporate)
echo    ✅ Evidence Management System
echo    ✅ Analytics Dashboard with Charts
echo    ✅ Case History & Session Tracking
echo    ✅ Enhanced AI with Legal Knowledge Base
echo    ✅ Professional UI with Navigation
echo    ✅ SQLite Database for Persistence
echo    ✅ JWT Token Authentication
echo    ✅ Advanced Objection System
echo.
echo 📋 FIRST TIME SETUP:
echo    1. Wait 10 seconds for services to start
echo    2. Open http://localhost:8501 in browser
echo    3. Register a new account (or login)
echo    4. Create your first case with enhanced options
echo    5. Experience professional courtroom simulation!
echo.
echo 💡 TIPS:
echo    - Try different case types for varied AI responses
echo    - Use the analytics dashboard to track performance
echo    - Explore evidence management features
echo    - Check case history for previous sessions
echo.
pause