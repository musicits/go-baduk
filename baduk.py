#!/usr/bin/env python3
"""바둑 게임 실행 스크립트.

    python baduk.py            # 브라우저로 바둑판 열기
    python baduk.py term       # 터미널에서 두기
    python baduk.py engines    # KataGo 설치 상태 보기

실제 구현은 `baduk/` 안에 있다.
"""

from baduk.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
