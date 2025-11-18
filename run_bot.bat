@echo off
REM Запуск massage_bot под виртуальным окружением .venv
REM Файл надо запускать из папки проекта (двойной клик или в терминале). 
setlocal

REM Перейти в каталог, где лежит батник
pushd %~dp0

REM Проверяем наличие активации venv
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo Виртуальное окружение не найдено: .venv\Scripts\activate.bat
  echo Создайте окружение командой: python -m venv .venv
  popd
  exit /b 1
)

echo Activated venv: %VIRTUAL_ENV%
echo Starting bot (Ctrl+C to stop)...

REM Запускаем основной скрипт через python из venv (явный путь)
".venv\Scripts\python.exe" "main.py"
set EXITCODE=%ERRORLEVEL%
echo Bot exited with code %EXITCODE%

popd
endlocal
exit /b %EXITCODE%
