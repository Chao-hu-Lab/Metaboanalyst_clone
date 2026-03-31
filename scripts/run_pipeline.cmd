@echo off
setlocal

python "%~dp0run_pipeline.py" %*
set EXITCODE=%ERRORLEVEL%

endlocal & exit /b %EXITCODE%
