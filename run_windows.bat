@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   SME FinancePilot - Windows Setup
echo ==========================================
if not exist .venv (
  py -m venv .venv
  if errorlevel 1 goto error
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo Starting SME FinancePilot...
streamlit run app.py
goto end
:error
echo.
echo Setup failed. Check that Python is installed and available as the py command.
pause
:end
endlocal
