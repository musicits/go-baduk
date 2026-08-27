#!/bin/bash
# 바둑 - 브라우저로 바둑판 열기
cd "$(dirname "$0")" || exit 1

echo "============================================"
echo "  바둑"
echo "============================================"
echo

# 바둑은 파이썬 기본 기능만 쓰므로 설치가 필요 없다.
# 사진 컬링 툴을 이미 설치했다면 그 파이썬을 그대로 쓴다.
if [ -x ".venv/bin/python" ]; then
    PY="./.venv/bin/python"
elif command -v python3 > /dev/null 2>&1; then
    PY="python3"
else
    echo "[오류] 파이썬을 찾을 수 없습니다."
    echo "      https://www.python.org 에서 파이썬 3.9 이상을 설치하세요."
    echo
    read -n 1 -s -r -p "아무 키나 누르면 닫힙니다..."
    exit 1
fi

echo "바둑판을 브라우저에 엽니다."
echo "KataGo 가 설치되어 있으면 KataGo 가, 없으면 내장 봇이 상대가 됩니다."
echo "(내장 봇은 아주 약합니다. 설치 방법은 README.md 를 보세요.)"
echo
echo "창을 닫으려면 이 터미널에서 Ctrl+C 를 누르세요."
echo

"$PY" baduk.py web

echo
read -n 1 -s -r -p "아무 키나 누르면 닫힙니다..."
