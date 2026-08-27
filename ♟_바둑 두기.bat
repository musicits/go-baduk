@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
title 바둑

echo ============================================
echo   바둑
echo ============================================
echo.

rem 바둑은 파이썬 기본 기능만 쓰므로 따로 설치할 게 없다.
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

where %PY% > nul 2>&1
if errorlevel 1 (
    if not exist ".venv\Scripts\python.exe" (
        echo [오류] 파이썬을 찾을 수 없습니다.
        echo        https://www.python.org 에서 파이썬 3.9 이상을 설치하세요.
        echo.
        pause
        exit /b 1
    )
)

echo 바둑판을 브라우저에 엽니다.
echo KataGo 가 설치되어 있으면 KataGo 가, 없으면 내장 봇이 상대가 됩니다.
echo (내장 봇은 아주 약합니다. 설치 방법은 README.md 를 보세요.)
echo.
echo 창을 닫으려면 이 창에서 Ctrl+C 를 누르세요.
echo.

"%PY%" baduk.py web

echo.
pause
