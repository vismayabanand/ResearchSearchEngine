@echo off
REM Check if all 3 arguments are provided
if "%~3"=="" (
    echo Usage: crawler.bat seed.txt MAX_DEPTH TIME_LIMIT
    exit /b
)

set "SEED_FILE=%~1"
set "MAX_DEPTH=%~2"
set "TIME_LIMIT=%~3"

REM Run the Python script with the seed file name
python crawler.py "%SEED_FILE%" %MAX_DEPTH% %TIME_LIMIT%
