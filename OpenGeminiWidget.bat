@echo off
REM Mo Gemini duoi dang mot cua so "app mode" nho gon (khong thanh tab/dia chi)
REM De ghim no luon noi phia truoc: cai Microsoft PowerToys > bat module "Always On Top"
REM Sau do focus vao cua so nay va bam Win+Ctrl+T

set "URL=https://gemini.google.com/"
set "W=420"
set "H=760"
set "X=1200"
set "Y=80"

REM Uu tien tim Brave, roi Coc Coc, roi moi den Chrome/Edge
set "BRAVE=%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"
if not exist "%BRAVE%" set "BRAVE=%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"
if not exist "%BRAVE%" set "BRAVE=%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"

set "COCCOC=%LocalAppData%\CocCoc\Browser\Application\browser.exe"
if not exist "%COCCOC%" set "COCCOC=%ProgramFiles%\CocCoc\Browser\Application\browser.exe"
if not exist "%COCCOC%" set "COCCOC=%ProgramFiles(x86)%\CocCoc\Browser\Application\browser.exe"

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"

set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if exist "%BRAVE%" (
    start "" "%BRAVE%" --app=%URL% --window-size=%W%,%H% --window-position=%X%,%Y%
    exit /b 0
)

if exist "%COCCOC%" (
    start "" "%COCCOC%" --app=%URL% --window-size=%W%,%H% --window-position=%X%,%Y%
    exit /b 0
)

if exist "%CHROME%" (
    start "" "%CHROME%" --app=%URL% --window-size=%W%,%H% --window-position=%X%,%Y%
    exit /b 0
)

if exist "%EDGE%" (
    start "" "%EDGE%" --app=%URL% --window-size=%W%,%H% --window-position=%X%,%Y%
    exit /b 0
)

echo Khong tim thay Chrome hoac Edge. Dang mo bang trinh duyet mac dinh...
start "" "%URL%"
