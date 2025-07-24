@echo off
SETLOCAL
set OSGEO4W_ROOT=C:/Program Files/QGIS 3.40.6
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
start /B python .\PAFyCToolsApp.py
REM start /min python .\PAFyCTools.py # graphic also minimized
ENDLOCAL
