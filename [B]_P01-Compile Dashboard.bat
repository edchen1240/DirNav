@echo off
cd /d "%~dp001_scripts"
:loop
echo Compiling DirNav dashboard from projects.json ...
echo.
python "P01_generate DirNav page.py"
echo.
if errorlevel 1 (
  echo COMPILE FAILED. Fix the error shown above in projects.json, then press ENTER to retry.
) else (
  echo Done. Refresh your browser tab to see the update.
)
echo.
echo Press ENTER to recompile, or close this window / Ctrl+C to exit.
pause >nul
goto loop
