@echo off
chcp 949 > nul
cd /d "%~dp0"
title KataGo 설치
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0KataGo 설치.ps1" %1
