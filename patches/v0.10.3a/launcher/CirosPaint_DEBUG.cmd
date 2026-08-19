@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo El entorno local aun no existe.
    echo Ejecuta primero CirosPaint.cmd para preparar Ciros Paint.
    echo.
    pause
    exit /b 1
)

echo Iniciando Ciros Paint 0.10.3a con consola de diagnostico...
echo.
".venv\Scripts\python.exe" "%~dp0main.py"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Ciros Paint ha terminado con codigo %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
