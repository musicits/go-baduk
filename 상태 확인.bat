@echo off
chcp 949 > nul
cd /d "%~dp0"
title 바둑 - 상태 확인

echo ============================================
echo   상태 확인
echo ============================================
echo.

set "PY="
py -3 --version > nul 2>&1 && set "PY=py -3"
if not defined PY python --version > nul 2>&1 && set "PY=python"
if not defined PY python3 --version > nul 2>&1 && set "PY=python3"

if not defined PY (
    echo [ X ] 파이썬이 없습니다.
    echo.
    echo       https://www.python.org/downloads/ 에서 내려받으세요.
    echo       설치 첫 화면에서 "Add python.exe to PATH" 를 꼭 체크하세요.
    echo.
    echo       파이썬 없이 두시려면 웹으로 가세요:
    echo       https://musicits.github.io/go-baduk/
    echo.
    pause
    exit /b 1
)

echo [ O ] 파이썬:
%PY% --version
echo.
echo 엔진 상태:
%PY% baduk.py engines
echo.
echo --------------------------------------------
echo KataGo 의 "설치됨" 이 false 면 "KataGo 설치.bat" 을 실행하세요.
echo.
pause
