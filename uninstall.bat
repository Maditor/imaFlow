@echo off
title AI Redraw Panel - Go cai dat

set "EXT_NAME=Remini"
set "DEST_DIR=%APPDATA%\Adobe\CEP\extensions\%EXT_NAME%"

echo Dang go cai dat %EXT_NAME%...
echo.

if exist "%DEST_DIR%" (
    rmdir /s /q "%DEST_DIR%"
    echo Da go cai dat thanh cong.
    echo Hay khoi dong lai Photoshop de ap dung thay doi.
) else (
    echo Khong tim thay extension da cai tai:
    echo %DEST_DIR%
)

echo.
pause
