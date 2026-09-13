@echo off
rem ---------------------------------------------------------------------------
rem Royal Wellness - lanzador para Windows.
rem
rem   actualizar.bat              -> reconstruye la web en docs\
rem   actualizar.bat --publicar   -> ademas hace commit y push (web en vivo)
rem
rem Existe porque en PowerShell el comando "bash" resuelve a WSL, donde NO hay
rem python ni gh. Este .bat llama a Git Bash explicitamente, que si los ve.
rem ---------------------------------------------------------------------------
setlocal
set "GITBASH=C:\Program Files\Git\bin\bash.exe"
if not exist "%GITBASH%" set "GITBASH=C:\Program Files (x86)\Git\bin\bash.exe"
if not exist "%GITBASH%" goto sinbash
cd /d "%~dp0"
"%GITBASH%" actualizar.sh %*
goto :eof

:sinbash
echo.
echo   ERROR: no encuentro Git Bash.
echo   Instalalo desde https://git-scm.com/download/win
echo.
exit /b 1
