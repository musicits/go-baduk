@echo off
chcp 949 > nul
cd /d "%~dp0"
title KataGo 설치
rem 첫 인자: 설치 경로 (비우면 이 폴더의 부모 아래 katago)
rem 둘째 인자: cpu 를 주면 그래픽카드 없이 도는 판을 받는다
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0KataGo 설치.ps1" %1 %2
