"""바둑 — 파이썬으로 만든 바둑판과 대국 프로그램.

* `baduk.board` — 규칙 (착수·따냄·패·계가)
* `baduk.gtp` — KataGo 등 GTP 엔진 연결
* `baduk.engine` — 대국 상대 고르기 (KataGo / 내장 봇)
* `baduk.game` — 대국 진행
* `baduk.sgf` — 기보 저장·불러오기
* `baduk.server` — 브라우저 바둑판
* `baduk.cli` — 터미널 대국
"""

from .board import BLACK, WHITE, EMPTY, PASS, Board, IllegalMove
from .game import Game, new_game

__all__ = [
    "BLACK", "WHITE", "EMPTY", "PASS",
    "Board", "IllegalMove", "Game", "new_game",
]
__version__ = "0.1.0"
