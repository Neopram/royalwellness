@echo off
rem ---------------------------------------------------------------------------
rem Royal Wellness - puesta en marcha inicial. Ejecutar UNA sola vez.
rem Crea el repo en GitHub, sube la web y activa GitHub Pages.
rem Llama a Git Bash porque el "bash" de PowerShell es WSL y ahi no hay gh.
rem ---------------------------------------------------------------------------
setlocal
set "GITBASH=C:\Program Files\Git\bin\bash.exe"
if not exist "%GITBASH%" set "GITBASH=C:\Program Files (x86)\Git\bin\bash.exe"
if not exist "%GITBASH%" goto sinbash
cd /d "%~dp0"
"%GITBASH%" scripts/init_repo.sh
goto :eof

:sinbash
echo.
echo   ERROR: no encuentro Git Bash.
echo   Instalalo desde https://git-scm.com/download/win
echo.
exit /b 1
