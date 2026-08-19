@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "READY_MARKER=.venv\.cirospaint-ready-0.10.3a"

if exist ".venv\Scripts\pythonw.exe" if exist "%READY_MARKER%" goto launch

echo.
echo Ciros Paint 0.10.3a - preparacion del entorno personal
echo La primera ejecucion puede tardar unos minutos.
echo.

set "BOOTSTRAP="

py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if not errorlevel 1 set "BOOTSTRAP=py -3.12"

if not defined BOOTSTRAP (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
    if not errorlevel 1 set "BOOTSTRAP=python"
)

if not defined BOOTSTRAP if exist "%USERPROFILE%\miniconda3\python.exe" (
    "%USERPROFILE%\miniconda3\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
    if not errorlevel 1 set "BOOTSTRAP=^"%USERPROFILE%\miniconda3\python.exe^""
)

if not defined BOOTSTRAP (
    for /d %%D in ("%USERPROFILE%\miniconda3\envs\*") do if not defined BOOTSTRAP (
        if exist "%%D\python.exe" (
            "%%D\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
            if not errorlevel 1 set "BOOTSTRAP=^"%%D\python.exe^""
        )
    )
)

if not defined BOOTSTRAP if exist "%USERPROFILE%\anaconda3\python.exe" (
    "%USERPROFILE%\anaconda3\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
    if not errorlevel 1 set "BOOTSTRAP=^"%USERPROFILE%\anaconda3\python.exe^""
)

if not defined BOOTSTRAP (
    echo No se ha encontrado Python 3.12.
    echo Instala Python 3.12 o Miniconda y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno local de Ciros Paint...
    %BOOTSTRAP% -m venv .venv
    if errorlevel 1 goto setup_error
)

echo Instalando o actualizando dependencias de Ciros Paint...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto setup_error

>"%READY_MARKER%" echo ready

:launch
if not exist ".venv\Scripts\pythonw.exe" goto setup_error
start "" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
exit /b 0

:setup_error
echo.
echo No se pudo preparar Ciros Paint.
echo Puedes abrir CirosPaint_DEBUG.cmd para ver el error con detalle.
echo.
pause
exit /b 1
