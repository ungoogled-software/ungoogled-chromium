:: https://github.com/Eloston/ungoogled-chromium/blob/master/BUILDING.md

:: buildkit-launcher.py creates symlinks so needs to be run as admin

:: edit these paths as required
@echo off
setlocal
set root=%~dp0
set python2=C:\Python27
:: this assumes that python 3, git, and 7za are already in your PATH. if not, uncomment and edit thhe line below
:: set PATH=C:\Dir\Containing\Python3;C:\Dir\Containing\Git;C:\Dir\Containing\7za

if not exist "%root%\ungoogled-chromium" goto :download

:menu
set /p response=refresh sources before building? (y/n): 
if "%response%"=="y" goto :download
if "%response%"=="Y" goto :download
if "%response%"=="n" goto :build
if "%response%"=="N" goto :build
echo please choose either "y" or "n"
echo choose "y" if unsure
goto :menu

:download
if not exist "%root%" mkdir "%root%"
cd "%root%"
if exist "%root%\ungoogled-chromium" rd /s /q "%root%\ungoogled-chromium"

title cloning git repo
@git clone git://github.com/Eloston/ungoogled-chromium
cd "%root%\ungoogled-chromium"

mkdir "%root%\ungoogled-chromium\buildspace\downloads"
title generating buildspace
@python buildkit-launcher.py genbun windows
@python buildkit-launcher.py getsrc
@python buildkit-launcher.py genbun subdom
@python buildkit-launcher.py genpkg windows
@python buildspace\tree\ungoogled_packaging\scripts\apply_patch_series.py


:build
cd %root%\ungoogled-chromium
:: ninja (called by build.bat) uses python 2
set PATH=%python2%;%python2%\Scripts;%PATH%
title installing python2 modules
@pip2 install pywin32 pypiwin32
title building
@cmd /c buildspace\tree\ungoogled_packaging\build.bat
title packaging
@cmd /c buildspace\tree\ungoogled_packaging\package.bat
title complete
cd %root%
pause
