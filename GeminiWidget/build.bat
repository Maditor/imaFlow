@echo off
title GeminiWidget - Build .exe

echo ================================================
echo   Dong goi GeminiWidget thanh file .exe
echo ================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [LOI] Chua cai Python. Hay tai va cai tai: https://www.python.org/downloads/
    echo Nho tick "Add python.exe to PATH" khi cai.
    pause
    exit /b 1
)

echo [1/3] Dang cai thu vien can thiet...
python -m pip install --upgrade pip >nul
python -m pip install pyinstaller pystray pillow
if errorlevel 1 (
    echo [LOI] Cai thu vien that bai. Kiem tra ket noi mang roi thu lai.
    pause
    exit /b 1
)

echo.
echo [2/3] Dang dong goi thanh .exe (co the mat 1-2 phut)...
python -m PyInstaller --onefile --noconsole --name GeminiWidget --icon=icon.ico gemini_widget.py
if errorlevel 1 (
    echo [LOI] Dong goi that bai.
    pause
    exit /b 1
)

echo.
echo [3/3] Hoan tat!
echo File exe nam tai: dist\GeminiWidget.exe
echo Anh co the copy file nay ra Desktop hoac ghim vao Taskbar de dung nhanh.
echo (Cac thu muc build\ va file .spec co the xoa, khong can giu lai)
echo.
pause
