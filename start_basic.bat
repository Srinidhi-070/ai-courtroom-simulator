@echo off
REM =====================================================
REM AI COURTROOM SIMULATOR - Clean Startup Script
REM =====================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

cls
echo.
echo ======================================================================
echo                    AI COURTROOM SIMULATOR
echo                      STARTUP SEQUENCE
echo ======================================================================
echo.

REM Check if venv exists
if not exist "venv" (
    echo [ERROR] Virtual environment not found!
    echo Please create it with: python -m venv venv
    echo Then install dependencies: .\venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo [STEP 1] Checking Python environment...
.\venv\Scripts\python.exe --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in venv!
    pause
    exit /b 1
)
echo [✓] Python venv is ready

echo [STEP 2] Checking Ollama AI Service...
netstat -ano 2>nul | findstr ":11434" >nul 2>&1
if errorlevel 1 (
    echo [!] Ollama not detected on port 11434
    echo To enable AI features, run: ollama serve
    echo The app will work with fallback responses.
    timeout /t 2 /nobreak
) else (
    echo [✓] Ollama is running on port 11434
)

echo [STEP 3] Starting FastAPI Backend (port 8000)...
start "FastAPI Backend" cmd /k "cd /d "%~dp0" && .\venv\Scripts\python.exe server.py"

timeout /t 3 /nobreak

echo [STEP 4] Starting Streamlit Frontend (port 8501)...
start "Streamlit Frontend" cmd /k "cd /d "%~dp0" && .\venv\Scripts\python.exe -m streamlit run app.py"

echo.
echo ======================================================================
echo                    STARTUP COMPLETE!
echo ======================================================================
echo.
echo 📍 URLS:
echo    Frontend: http://localhost:8501
echo    Backend:  http://127.0.0.1:8000
echo    Health:   http://127.0.0.1:8000/health
echo.
echo 💡 Wait 5-10 seconds then open http://localhost:8501
echo.
pause