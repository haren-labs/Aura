@echo off
chcp 65001 > nul
echo Creo il collegamento di Aura sul Desktop...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut($d+'\Aura.lnk'); $s.TargetPath='%~dp0avvia_aura.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0aura_blu.ico'; $s.Description='Avvia Aura'; $s.Save()"
echo.
echo Fatto! Trovi "Aura" sul Desktop.
pause
