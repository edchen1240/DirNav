@echo off
echo Registering the kickoff:// protocol for the CURRENT Windows user ...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp001_scripts\Install-Protocol.ps1"
echo.
echo Verifying it landed in YOUR registry hive:
reg query "HKCU\Software\Classes\kickoff" /ve
echo.
echo If the key shows above, FULLY quit Chrome:
echo   - close every Chrome window, AND
echo   - end any leftover chrome.exe in Task Manager (or run: taskkill /F /IM chrome.exe)
echo Then reopen with [B]_localhost homepage.bat and click a button.
pause
