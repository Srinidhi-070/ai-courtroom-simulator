@echo off
REM =====================================================
REM AI COURTROOM SIMULATOR - SIMPLE WORKING VERSION
REM =====================================================

cd /d "%~dp0"

cls
echo.
echo ======================================================================
echo                    AI COURTROOM SIMULATOR
echo                      SIMPLE WORKING VERSION
echo ======================================================================
echo.

echo [STEP 1] Installing dependencies...
pip install -r requirements_simple.txt --quiet
echo [✓] Dependencies installed

echo.
echo [STEP 2] Starting Backend Server...
start "Backend Server" cmd /k "python server_simple.py"

echo Waiting for backend to start...
timeout /t 3 /nobreak

echo.
echo [STEP 3] Starting Frontend...
start "Frontend" cmd /k "python -m streamlit run app_simple.py"

echo.
echo ======================================================================
echo                    READY TO USE!
echo ======================================================================
echo.
echo 🌐 Frontend: http://localhost:8501
echo 🔧 Backend:  http://127.0.0.1:8000
echo.
echo 📋 INSTRUCTIONS:
echo 1. Wait 10 seconds for services to start
echo 2. Browser will open automatically to http://localhost:8501
echo 3. Fill in case title and facts
echo 4. Choose your role (defense/prosecution/judge)
echo 5. Click "Start Court Session"
echo 6. Type arguments and click "Submit Argument"
echo.
echo 💡 NOTE: If Ollama is running, you'll get AI responses.
echo          If not, you'll get fallback responses (still works!)
echo.
pause