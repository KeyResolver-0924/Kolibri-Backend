@echo off
echo Activating Python virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated!
echo.
echo To start the backend server, run:
echo   python main.py
echo.
echo To install dependencies, run:
echo   pip install -r requirements.txt
echo.
cmd /k 