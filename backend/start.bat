@echo off
echo ============================================
echo  AML Sentinel Backend — FastAPI
echo ============================================
echo.

:: Activate venv
call C:\Users\VatsaL\Desktop\Datasets\AML_Sentinel\.venv\Scripts\activate.bat

:: Install backend deps if needed
pip install fastapi uvicorn[standard] pydantic --quiet --break-system-packages

:: Start FastAPI
echo Starting FastAPI on http://localhost:8000
echo API Docs at  http://localhost:8000/docs
echo.
cd /d C:\Users\VatsaL\Desktop\Datasets\AML_Sentinel\backend
python main.py

pause