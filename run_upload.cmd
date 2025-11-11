@echo off
REM ============================================================================
REM Script Batch Windows : Upload avec Granularite Maximale
REM ============================================================================
REM Usage : run_upload.cmd
REM ============================================================================

setlocal EnableDelayedExpansion

REM Configuration par defaut
set INPUT_PATH=c:\OneDriveExport
set GRANULARITY=ULTRA_FINE
set WORKERS=3
set UPLOAD=1
set OCR=1

REM ============================================================================
REM Verification Python
REM ============================================================================

echo.
echo ================================================================================
echo   VERIFICATION DE L'ENVIRONNEMENT
echo ================================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python n'est pas installe ou n'est pas dans le PATH
    echo     Installez Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Python trouve : !PYTHON_VERSION!

REM ============================================================================
REM Verification du repertoire d'entree
REM ============================================================================

if not exist "%INPUT_PATH%" (
    echo.
    echo [X] Le repertoire d'entree n'existe pas : %INPUT_PATH%
    echo     Modifiez INPUT_PATH dans ce script ou creez le repertoire
    pause
    exit /b 1
)

echo [OK] Repertoire d'entree : %INPUT_PATH%

REM ============================================================================
REM Verification .env
REM ============================================================================

if not exist ".env" (
    echo.
    echo [i] Fichier .env non trouve, creation depuis .env.example...
    copy .env.example .env >nul
    echo [OK] Fichier .env cree
    echo.
    echo *** IMPORTANT ***
    echo Editez le fichier .env avec vos cles API avant de continuer !
    echo.
    echo Configuration requise :
    echo   - OPENAI_API_KEY
    echo   - SUPABASE_URL
    echo   - SUPABASE_KEY
    echo.
    notepad .env
    echo.
    set /p CONFIRM="Avez-vous configure le fichier .env ? (o/n) : "
    if /i not "!CONFIRM!"=="o" (
        echo [X] Veuillez configurer .env avant de continuer
        pause
        exit /b 1
    )
) else (
    echo [OK] Fichier .env trouve
)

REM ============================================================================
REM Installation des dependances
REM ============================================================================

echo.
echo ================================================================================
echo   VERIFICATION DES DEPENDANCES
echo ================================================================================
echo.

echo [i] Verification des packages Python...

pip show openai >nul 2>&1
if errorlevel 1 (
    echo [i] Installation de openai...
    pip install -q openai
)

pip show supabase >nul 2>&1
if errorlevel 1 (
    echo [i] Installation de supabase...
    pip install -q supabase
)

pip show python-dotenv >nul 2>&1
if errorlevel 1 (
    echo [i] Installation de python-dotenv...
    pip install -q python-dotenv
)

pip show tenacity >nul 2>&1
if errorlevel 1 (
    echo [i] Installation de tenacity...
    pip install -q tenacity
)

pip show PyPDF2 >nul 2>&1
if errorlevel 1 (
    echo [i] Installation de PyPDF2...
    pip install -q PyPDF2
)

echo [OK] Dependances installees

REM ============================================================================
REM Configuration
REM ============================================================================

echo.
echo ================================================================================
echo   CONFIGURATION
echo ================================================================================
echo.

echo   Niveau de granularite : %GRANULARITY%

if "%GRANULARITY%"=="ULTRA_FINE" (
    echo     -^> 200 chars/chunk, 50 overlap (~60 chunks/10k caracteres^)
    echo     -^> Precision MAXIMALE
)
if "%GRANULARITY%"=="FINE" (
    echo     -^> 400 chars/chunk, 100 overlap (~30 chunks/10k caracteres^)
    echo     -^> Haute granularite (recommande^)
)

echo   Workers paralleles : %WORKERS%
echo   Repertoire d'entree : %INPUT_PATH%
if "%UPLOAD%"=="1" (
    echo   Upload Supabase : OUI
) else (
    echo   Upload Supabase : NON
)
if "%OCR%"=="1" (
    echo   Azure OCR : OUI
) else (
    echo   Azure OCR : NON
)

REM ============================================================================
REM Confirmation
REM ============================================================================

echo.
set /p CONFIRM="Continuer ? (o/n) : "
if /i not "!CONFIRM!"=="o" (
    echo [i] Operation annulee
    pause
    exit /b 0
)

REM ============================================================================
REM Lancement du traitement
REM ============================================================================

echo.
echo ================================================================================
echo   TRAITEMENT EN COURS
echo ================================================================================
echo.

REM Configurer la variable d'environnement
set GRANULARITY_LEVEL=%GRANULARITY%

REM Construire la commande
set CMD=python process_v2.py --input "%INPUT_PATH%" --workers %WORKERS%

if "%UPLOAD%"=="1" set CMD=!CMD! --upload
if "%OCR%"=="1" set CMD=!CMD! --use-ocr

echo [i] Commande : !CMD!
echo.

REM Creer le nom de fichier log
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set DATE=%%c%%b%%a)
for /f "tokens=1-2 delims=/: " %%a in ('time /t') do (set TIME=%%a%%b)
set LOGFILE=upload_%DATE%_%TIME%.log

echo [i] Logs sauvegardes dans : %LOGFILE%
echo.

REM Lancer le traitement
!CMD! 2>&1 | tee %LOGFILE%

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo   TRAITEMENT TERMINE AVEC ERREURS
    echo ================================================================================
    echo.
    echo [X] Code de sortie : %errorlevel%
    echo [i] Consultez le fichier log : %LOGFILE%
    pause
    exit /b %errorlevel%
)

REM ============================================================================
REM Resume
REM ============================================================================

echo.
echo ================================================================================
echo   TRAITEMENT TERMINE AVEC SUCCES
echo ================================================================================
echo.
echo [OK] Fichiers traites depuis : %INPUT_PATH%
echo [OK] Niveau de granularite : %GRANULARITY%
echo [OK] Workers utilises : %WORKERS%
echo [OK] Log complet : %LOGFILE%
echo.

if "%UPLOAD%"=="1" (
    echo Vos documents sont maintenant disponibles dans Supabase !
    echo Vous pouvez effectuer des recherches semantiques ultra-precises.
)

echo.
pause
