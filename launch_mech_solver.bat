@echo off
setlocal

rem Launch the Shigley solver Streamlit app.
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "problem_parsing_env\.venv\Scripts\activate.bat" (
    call "problem_parsing_env\.venv\Scripts\activate.bat"
)

python -m streamlit run ui\app_manual_solver.py %*
