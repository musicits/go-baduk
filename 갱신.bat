@echo off
chcp 949 > nul
cd /d "%~dp0"
title 바둑 - 최신으로 갱신

echo ============================================
echo   최신으로 갱신
echo ============================================
echo.

where git > nul 2>&1
if errorlevel 1 (
    echo [오류] git 이 없습니다.
    echo        https://git-scm.com/download/win 에서 설치하세요.
    echo.
    pause
    exit /b 1
)

git pull

echo.
if errorlevel 1 (
    echo [오류] 갱신하지 못했습니다. 위 내용을 그대로 알려주세요.
) else (
    echo 최신 상태입니다.
)
echo.
pause
