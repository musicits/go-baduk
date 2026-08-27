@echo off
chcp 949 > nul
setlocal
cd /d "%~dp0"
title 바둑 - 내려받기

echo ============================================
echo   바둑 내려받기
echo ============================================
echo.
echo 이 파일이 있는 폴더 아래에 "6. 바둑" 을 만듭니다.
echo.

where git > nul 2>&1
if errorlevel 1 (
    echo [오류] git 이 없습니다.
    echo.
    echo   https://git-scm.com/download/win 에서 설치하거나,
    echo   아래 주소에서 ZIP 으로 받아 압축을 푸셔도 됩니다.
    echo   https://github.com/musicits/go-baduk/archive/refs/heads/main.zip
    echo.
    pause
    exit /b 1
)

if exist "6. 바둑\.git" (
    echo 이미 받아둔 것이 있어 최신으로 갱신만 합니다.
    pushd "6. 바둑"
    git pull
    popd
) else (
    git clone https://github.com/musicits/go-baduk.git "6. 바둑"
)

if errorlevel 1 (
    echo.
    echo [오류] 받아오지 못했습니다. 인터넷 연결을 확인하세요.
    pause
    exit /b 1
)

echo.
echo 끝났습니다. "6. 바둑" 폴더 안의 바둑 두기 파일을 실행하세요.
echo 설치 없이 웹에서 두시려면: https://musicits.github.io/go-baduk/
echo.
pause
