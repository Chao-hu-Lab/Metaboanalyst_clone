@echo off
setlocal

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

scripts\run_pipeline.cmd -Config "%~2" -Input "%~1" %3 %4 %5 %6 %7 %8 %9
set EXITCODE=%ERRORLEVEL%

endlocal & exit /b %EXITCODE%

:usage
echo Usage:
echo   run.cmd "C:\path\to\input.xlsx" "configs\your_config.yaml"
echo   run.cmd "C:\path\to\input.xlsx" "configs\your_config.yaml" -Suffix "_rerun"
endlocal & exit /b 1
