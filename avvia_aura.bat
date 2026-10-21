@echo off
title AVVIO AURA
color 0B

REM ============ CONFIGURAZIONE (modifica qui) ============
set "COMFYUI_DIR=C:\ComfyUI"
set "DOCKER_EXE=C:\Program Files\Docker\Docker\Docker Desktop.exe"
set "CONTAINER_TTS=aura-tts"
set "PYTHON=python"
REM Se ComfyUI usa un Python diverso (es. la versione portable: C:\ComfyUI\python_embeded\python.exe), scrivilo qui
set "PYTHON_COMFYUI=%PYTHON%"
REM LM Studio: percorso del programma e nome ESATTO del modello (come in "lms ls")
set "LMSTUDIO_EXE=%LOCALAPPDATA%\Programs\LM Studio\LM Studio.exe"
set "MODELLO=gemma-4-e4b-uncensored-hauhaucs-aggressive"
REM =======================================================

cd /d "%~dp0"
echo.
echo  ================================================
echo   AURA - AVVIO IN CORSO...
echo  ================================================
echo.

echo [1/6] Controllo Docker Desktop...
docker info >nul 2>&1
if %errorlevel%==0 goto docker_ok
echo      Docker non attivo, lo avvio...
if exist "%DOCKER_EXE%" goto docker_lancia
echo      ATTENZIONE: Docker Desktop non trovato. Avvialo a mano o correggi DOCKER_EXE.
goto docker_attesa_init
:docker_lancia
start "" "%DOCKER_EXE%"
:docker_attesa_init
set /a tentativi=0
:docker_attesa
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if %errorlevel%==0 goto docker_ok
set /a tentativi+=1
if %tentativi% geq 36 goto docker_ko
echo      ...attendo il motore Docker
goto docker_attesa

:docker_ok
echo      OK - Docker attivo
echo.
echo [2/6] Avvio il container della voce (Edge TTS)...
docker start %CONTAINER_TTS% >nul 2>&1
if not errorlevel 1 goto voce_ok
echo      Creo il container della voce (prima volta)...
docker run -d --name %CONTAINER_TTS% -p 5050:5050 -e REQUIRE_API_KEY=False travisvn/openai-edge-tts:latest
echo      Aggiorno la libreria della voce (edge-tts): serve per evitare l'errore 403 di Microsoft...
set /a prove=0
:voce_pip
timeout /t 8 /nobreak >nul
docker exec %CONTAINER_TTS% pip install --upgrade edge-tts >nul 2>&1
if not errorlevel 1 goto voce_pip_ok
set /a prove+=1
if %prove% lss 3 goto voce_pip
echo      ATTENZIONE: aggiornamento di edge-tts non riuscito. Se la voce da' errore 403, vedi il README.
:voce_pip_ok
docker restart %CONTAINER_TTS% >nul 2>&1
:voce_ok
echo      OK - voce pronta
echo.
goto lmstudio

:docker_ko
echo      ERRORE: Docker non risponde dopo 3 minuti.
echo      Il resto parte comunque, ma Aura non potra' parlare.
echo.

:lmstudio
echo [3/6] Avvio LM Studio e carico il modello...
where lms >nul 2>&1
if errorlevel 1 goto lm_nolms
tasklist /FI "IMAGENAME eq LM Studio.exe" 2>nul | find /I "LM Studio.exe" >nul
if %errorlevel%==0 goto lm_server
if exist "%LMSTUDIO_EXE%" goto lm_lancia
echo      ATTENZIONE: LM Studio non trovato (correggi LMSTUDIO_EXE). Avvialo a mano.
goto lm_server
:lm_lancia
echo      LM Studio non attivo, lo avvio...
start "" "%LMSTUDIO_EXE%"
timeout /t 10 /nobreak >nul

:lm_server
set /a tentativi=0
:lm_server_prova
call lms server start >nul 2>&1
if %errorlevel%==0 goto lm_server_ok
set /a tentativi+=1
if %tentativi% geq 12 goto lm_ko
echo      ...attendo LM Studio
timeout /t 5 /nobreak >nul
goto lm_server_prova

:lm_server_ok
echo      OK - server LM Studio attivo su porta 1234
call lms ps 2>nul | find "%MODELLO%" >nul
if %errorlevel%==0 goto lm_gia_caricato
echo      Carico il modello (puo' richiedere un po')...
call lms load %MODELLO%
if %errorlevel%==0 goto lm_caricato
goto lm_ko
:lm_gia_caricato
echo      OK - modello gia' caricato
echo.
goto avanti
:lm_caricato
echo      OK - modello caricato
echo.
goto avanti

:lm_nolms
echo      ATTENZIONE: il comando "lms" non e' disponibile.
:lm_ko
echo      LM Studio non e' partito da solo: aprilo a mano, carica il modello
echo      e avvia il server locale (porta 1234).
echo.

:avanti
echo [4/6] Avvio ComfyUI...
if not exist "%COMFYUI_DIR%\main.py" goto comfy_ko
start "ComfyUI" /d "%COMFYUI_DIR%" cmd /k ""%PYTHON_COMFYUI%" main.py"
echo      OK - ComfyUI avviato su porta 8188
goto comfy_fine
:comfy_ko
echo      SALTATO: non trovo ComfyUI in %COMFYUI_DIR% (correggi COMFYUI_DIR). Senza ComfyUI niente immagini.
:comfy_fine
echo.

timeout /t 3 /nobreak > nul

echo [5/6] Avvio il server di Aura...
start "Aura Server" cmd /k ""%PYTHON%" aura_server.py"
echo      OK - server su porta 8888, dashboard su porta 8000
echo.

timeout /t 10 /nobreak > nul

echo [6/6] Apro la dashboard nel browser...
start "" "http://127.0.0.1:8000/aura_dashboard.html"
echo      OK - dashboard aperta
echo.

echo  ================================================
echo   AURA E' PRONTA!
echo  ================================================
echo.
echo  Premi un tasto per chiudere questa finestra...
pause > nul
