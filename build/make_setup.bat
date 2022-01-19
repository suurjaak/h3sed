:: Creates NSIS setup file for executable in current directory named
:: h3sed_%conf.Version%[_x64].exe, or filename given in argument.
:: Processor architecture is determined from OS environment.
::
:: @author    Erki Suurjaak
:: @created   21.08.2019
:: @modified  19.01.2022
@echo off
setlocal EnableDelayedExpansion
set INITIAL_DIR=%CD%
cd %0\..
set SETUPDIR=%CD%

cd ..\src

set SUFFIX64=
for /f %%i in ('python -c "import struct; print struct.calcsize(""P"") * 8"') do set ADDRSIZE=%%i
if "%ADDRSIZE%" equ "64" set SUFFIX64=_x64

if [%1] == [] (
    for /f %%I in ('python -c "from h3sed import conf; print conf.Version"') do set VERSION=%%I
    set EXEFILE=%INITIAL_DIR%\h3sed_!VERSION!%SUFFIX64%.exe
) else (
    for /f "tokens=2 delims=_ " %%a in ("%~n1") do set VERSION=%%a
    echo "VERSION2 = %VERSION%."
    set EXEFILE=%INITIAL_DIR%\%1
)

if not exist "%EXEFILE%" echo %EXEFILE% missing. && goto :END
set NSISDIR=C:\Program Files (x86)\Nullsoft Scriptable Install System
if not exist "%NSISDIR%" set NSISDIR=C:\Program Files\Nullsoft Scriptable Install System
if not exist "%NSISDIR%" set NSISDIR=C:\Program Files (x86)\NSIS
if not exist "%NSISDIR%" set NSISDIR=C:\Program Files\NSIS
if not exist "%NSISDIR%\makensis.exe" echo NSIS not found. && goto :END

echo Creating installer for h3sed %VERSION%%SUFFIX64%.
cd %SETUPDIR%
set DESTFILE=h3sed_%VERSION%%SUFFIX64%_setup.exe
if exist "%DESTFILE%" echo Removing previous %DESTFILE%. & del "%DESTFILE%"
if exist h3sed.exe del h3sed.exe
copy /V "%EXEFILE%" h3sed.exe > NUL 2>&1
"%NSISDIR%\makensis.exe" /DVERSION=%VERSION% /DSUFFIX64=%SUFFIX64% "%SETUPDIR%\exe_setup.nsi"
del h3sed.exe > NUL 2>&1
if exist "%DESTFILE%" echo. & echo Successfully created h3sed source distribution %DESTFILE%.
move "%DESTFILE%" "%INITIAL_DIR%" > NUL 2>&1

:END
cd "%INITIAL_DIR%"
