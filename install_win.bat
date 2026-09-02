@echo off
setlocal enabledelayedexpansion
title AI Redraw Panel - Trinh cai dat CEP cho Photoshop

set "EXT_NAME=Remini"
set "SRC_DIR=%~dp0%EXT_NAME%"
set "DEST_DIR=%APPDATA%\Adobe\CEP\extensions\%EXT_NAME%"

echo ================================================
echo    AI Redraw Panel - Trinh cai dat cho Photoshop
echo ================================================
echo.

REM ---- 1. Kiem tra thu muc extension co ton tai khong ----
if not exist "%SRC_DIR%" (
    echo [LOI] Khong tim thay thu muc "%EXT_NAME%" nam cung cap voi file install.bat nay.
    echo Hay chac chan ban KHONG di chuyen rieng file install.bat ra khoi thu muc goc.
    echo.
    pause
    exit /b 1
)

REM ---- 2. Bat PlayerDebugMode de Photoshop chap nhan extension chua ky ----
echo [1/3] Dang bat che do Debug cho CEP...
for %%V in (6 7 8 9 10 11 12) do (
    reg add "HKCU\Software\Adobe\CSXS.%%V" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul 2>&1
)
echo       -^> Da bat PlayerDebugMode cho CSXS.6 den CSXS.12

REM ---- 3. Copy extension vao thu muc CEP cua Adobe ----
echo.
echo [2/3] Dang sao chep extension...
if exist "%DEST_DIR%" (
    echo       -^> Phat hien ban cai dat cu, dang go bo...
    rmdir /s /q "%DEST_DIR%"
)
if not exist "%APPDATA%\Adobe\CEP\extensions" (
    mkdir "%APPDATA%\Adobe\CEP\extensions" >nul 2>&1
)
xcopy "%SRC_DIR%" "%DEST_DIR%\" /E /I /H /Y >nul

if not exist "%DEST_DIR%\CSXS\manifest.xml" (
    echo [LOI] Sao chep khong thanh cong. Vui long thu lai hoac copy thu cong.
    echo Thu muc dich: %DEST_DIR%
    pause
    exit /b 1
)
echo       -^> Da cai vao: %DEST_DIR%

REM ---- 4. Hoan tat ----
echo.
echo [3/3] Cai dat hoan tat!
echo.
echo    Hay KHOI DONG LAI Photoshop, sau do vao:
echo    Window ^> Extensions ^> AI Redraw Panel
echo.
echo ================================================
pause
