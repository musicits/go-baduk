@echo off
chcp 949 > nul
setlocal
cd /d "%~dp0"
title 바둑

echo ============================================
echo   바둑
echo ============================================
echo.

rem 파이썬을 찾는다. py 런처를 가장 먼저 본다 (가장 확실하다).
set "PY="
py -3 --version > nul 2>&1 && set "PY=py -3"
if not defined PY python --version > nul 2>&1 && set "PY=python"
if not defined PY python3 --version > nul 2>&1 && set "PY=python3"

if not defined PY (
    echo [오류] 파이썬을 찾을 수 없습니다.
    echo.
    echo   1. https://www.python.org/downloads/ 에서 내려받으세요.
    echo   2. 설치 첫 화면에서 "Add python.exe to PATH" 를 꼭 체크하세요.
    echo   3. 설치한 뒤 이 파일을 다시 실행하세요.
    echo.
    echo   설치가 번거로우면 웹에서 바로 두셔도 됩니다.
    echo   https://musicits.github.io/go-baduk/
    echo.
    pause
    exit /b 1
)

echo 파이썬을 찾았습니다.
%PY% --version
echo.
echo 바둑판을 브라우저에 엽니다.
echo KataGo 가 설치되어 있으면 KataGo 가, 없으면 내장 봇이 상대가 됩니다.
echo.
echo 창을 닫으려면 이 창에서 Ctrl+C 를 누르세요.
echo.

%PY% baduk.py web

echo.
if errorlevel 1 (
    echo [오류] 실행하지 못했습니다. 위 내용을 그대로 알려주세요.
)
pause
