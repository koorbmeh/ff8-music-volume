@echo off
title FF8 Music Volume
cd /d "%~dp0"
set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py"
if not defined PYEXE ( where python >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE (
  echo.
  echo   Python 3 was not found on your PC.
  echo   Install it from https://www.python.org/downloads/  ^(check "Add Python to PATH"^),
  echo   then double-click this file again.
  echo.
  pause
  exit /b 1
)
%PYEXE% "%~dp0ff8_music_volume.py" %*
