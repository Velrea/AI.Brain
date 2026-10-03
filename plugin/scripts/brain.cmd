@echo off
rem Runs the Brain's launcher with this machine's own Python 3.11 or later:
rem python, or else the py launcher. brain beside it does the same elsewhere.
setlocal
set "launch=%~dp0..\server\launch.py"
python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && goto python
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && goto py
echo The Brain needs Python 3.11 or later, as python or py on the PATH. 1>&2
exit /b 1

:python
python "%launch%" %*
exit /b %errorlevel%

:py
py -3 "%launch%" %*
exit /b %errorlevel%
