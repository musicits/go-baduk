"""대국 상대(엔진) 고르기.

두 종류가 있다.

* `EngineBot` — KataGo 같은 GTP 엔진을 붙여서 둔다. 실력은 엔진 실력이다.
* `BuiltinBot` — 아무것도 깔지 않아도 도는 내장 봇. **아주 약하다.**
  규칙과 화면이 도는지 확인하는 용도지, 실력을 겨룰 상대가 아니다.

`load_engine()` 은 KataGo 가 깔려 있으면 그걸 쓰고, 없으면 내장 봇으로
조용히 물러난다. 그래서 설치 없이도 프로그램이 그냥 돈다.
"""

from __future__ import annotations

import json
import os
import random
import shutil
from pathlib import Path

from .board import BLACK, WHITE, EMPTY, PASS, Board, opponent, star_points
from .gtp import GtpEngine, GtpError, EngineNotFound


# KataGo 를 찾아볼 곳들. 환경변수가 가장 우선한다.
_KATAGO_ENV = "KATAGO_PATH"
_CONFIG_ENV = "KATAGO_CONFIG"
_MODEL_ENV = "KATAGO_MODEL"

_SEARCH_DIRS = [
    Path.home() / ".katago",
    Path.home() / "katago",
    Path.home() / "Downloads" / "katago",
    Path("/usr/local/share/katago"),
    Path("/opt/katago"),
    Path("/opt/homebrew/share/katago"),
    Path("C:/katago"),
    Path("C:/Program Files/katago"),
]


class Player:
    """대국자 공통 껍데기."""

    name = "대국자"
    strength = ""

    def setup(self, board: Board):
        """대국 시작 전에 판 정보를 알린다."""

    def observe(self, color: int, move):
        """상대가 둔 수를 알린다."""

    def genmove(self, board: Board, color: int):
        """둘 자리를 돌려준다. `PASS` 또는 문자열 ``"resign"`` 도 된다."""
        raise NotImplementedError

    def analyze(self, board: Board, color: int):
        """승률 정보를 돌려준다. 못 하면 빈 리스트."""
        return []

    def close(self):
        """정리한다."""


class EngineBot(Player):
    """GTP 엔진(KataGo 등)을 대국 상대로 쓴다."""

    def __init__(self, engine: GtpEngine, think_time: float = 5.0,
                 strength: str = ""):
        self.engine = engine
        self.think_time = think_time
        self.name = engine.name
        self.strength = strength or "엔진 실력"
        self._board_size = None

    def setup(self, board: Board):
        self.engine.start()
        self.name = self.engine.version() or self.engine.name
        self.engine.boardsize(board.size)
        self.engine.komi(board.komi)
        self._board_size = board.size
        # 이미 둔 수가 있으면(접바둑·불러온 기보) 엔진에 그대로 옮긴다.
        for idx, stone in enumerate(board.stones):
            if stone != EMPTY and not board.moves:
                self.engine.send(
                    f"play {'black' if stone == BLACK else 'white'} "
                    f"{board.to_gtp(board.coord(idx))}"
                )
        for color, move in board.moves:
            self.engine.play(color, board.to_gtp(move))

    def observe(self, color: int, move):
        vertex = "pass" if move is PASS else _vertex(self._board_size, move)
        try:
            self.engine.play(color, vertex)
        except GtpError:
            pass

    def genmove(self, board: Board, color: int):
        vertex = self.engine.genmove(color, timeout=max(30.0, self.think_time * 20))
        if vertex == "resign":
            return "resign"
        if vertex in ("pass", ""):
            return PASS
        try:
            return board.from_gtp(vertex)
        except ValueError:
            return PASS

    def analyze(self, board: Board, color: int):
        try:
            return self.engine.analyze(color, centiseconds=int(self.think_time * 100))
        except GtpError:
            return []

    def dead_stones(self, board: Board):
        """엔진이 죽었다고 보는 돌 좌표."""
        out = []
        for vertex in self.engine.dead_stones():
            try:
                out.append(board.from_gtp(vertex))
            except ValueError:
                pass
        return out

    def close(self):
        self.engine.stop()


class BuiltinBot(Player):
    """설치 없이 도는 내장 봇. 아주 약하다.

    돌을 따고, 단수 맞은 돌을 살리고, 자기 눈은 안 메우는 정도만 한다.
    정석도 사활도 모른다. KataGo 를 붙이면 이 봇은 안 쓰인다.
    """

    name = "내장 봇"
    strength = "아주 약함 (연습용)"

    def __init__(self, seed: int = None, pass_when_behind: bool = True):
        self.random = random.Random(seed)
        self.pass_when_behind = pass_when_behind
        self._last = None

    def observe(self, color: int, move):
        if move is not PASS:
            self._last = move

    def genmove(self, board: Board, color: int):
        candidates = board.legal_moves(color)
        candidates = [m for m in candidates if not self._is_own_eye(board, m, color)]
        if not candidates:
            return PASS

        best, best_score = None, float("-inf")
        for move in candidates:
            score = self._score(board, move, color)
            score += self.random.random() * 0.4
            if score > best_score:
                best, best_score = move, score

        # 둘 데가 남았어도 이득이 없으면 패스해서 판을 끝낸다.
        if self.pass_when_behind and best_score < 0.5 and len(board.moves) > board.size * board.size // 3:
            return PASS
        return best

    # -- 내부 판단 -----------------------------------------------------
    def _score(self, board: Board, move, color: int) -> float:
        size = board.size
        enemy = opponent(color)
        idx = board.index(move)
        score = 0.0

        for j in board._neighbors[idx]:
            stone = board.stones[j]
            if stone == EMPTY:
                continue
            group, libs = board._group_at(j)
            if stone == enemy and len(libs) == 1:
                score += 12.0 + 2.0 * len(group)     # 따낸다
            elif stone == enemy and len(libs) == 2:
                score += 2.5                          # 단수 친다
            elif stone == color and len(libs) == 1:
                score += 9.0 + 1.5 * len(group)      # 살린다
            elif stone == color and len(libs) == 2:
                score += 1.5                          # 늘어둔다

        # 놓고 나서 내 활로가 몇 개인지 본다.
        board.stones[idx] = color
        try:
            _, libs = board._group_at(idx)
            after = len(libs)
        finally:
            board.stones[idx] = EMPTY
        if after <= 1:
            score -= 6.0
        else:
            score += min(after, 4) * 0.5

        row, col = move
        edge = min(row, col, size - 1 - row, size - 1 - col)
        if len(board.moves) < size:               # 포석엔 귀·변
            if move in star_points(size):
                score += 4.0
            score += 2.0 if edge == 3 else 0.0
        if edge == 0:
            score -= 3.0                          # 1선은 피한다
        elif edge == 1:
            score -= 1.0

        if self._last is not None:                # 상대 수 근처에 응수
            dist = abs(row - self._last[0]) + abs(col - self._last[1])
            if dist <= 3:
                score += 2.0 - dist * 0.4
        return score

    def _is_own_eye(self, board: Board, move, color: int) -> bool:
        """자기 눈이면 True. 눈을 메우면 스스로 죽기 때문에 피한다."""
        idx = board.index(move)
        for j in board._neighbors[idx]:
            if board.stones[j] != color:
                return False
        row, col = move
        size = board.size
        diagonals = [
            (row + dr, col + dc)
            for dr in (-1, 1) for dc in (-1, 1)
            if 0 <= row + dr < size and 0 <= col + dc < size
        ]
        enemy = opponent(color)
        bad = sum(1 for d in diagonals if board.get(d) == enemy)
        on_edge = len(diagonals) < 4
        return bad == 0 if on_edge else bad <= 1


# ----------------------------------------------------------------------
# KataGo 찾기
# ----------------------------------------------------------------------
def find_katago():
    """KataGo 실행 파일·설정·신경망을 찾는다.

    :return: ``{"실행": path, "설정": path, "신경망": path}``.
        실행 파일을 못 찾으면 None.
    """
    binary = os.environ.get(_KATAGO_ENV) or shutil.which("katago")
    if binary and not Path(binary).exists() and not shutil.which(binary):
        binary = None
    if not binary:
        for folder in _SEARCH_DIRS:
            for name in ("katago", "katago.exe"):
                candidate = folder / name
                if candidate.is_file():
                    binary = str(candidate)
                    break
            if binary:
                break
    if not binary:
        return None

    home = Path(binary).resolve().parent
    config = os.environ.get(_CONFIG_ENV) or _first_match(
        [home, *_SEARCH_DIRS], ("gtp_custom.cfg", "gtp_example.cfg", "*.cfg")
    )
    model = os.environ.get(_MODEL_ENV) or _first_match(
        [home, *_SEARCH_DIRS], ("*.bin.gz", "*.txt.gz", "*.bin")
    )
    return {"실행": binary, "설정": config, "신경망": model}


def _first_match(folders, patterns):
    for folder in folders:
        folder = Path(folder)
        if not folder.is_dir():
            continue
        for pattern in patterns:
            hits = sorted(folder.glob(pattern))
            if hits:
                return str(hits[0])
        for sub in ("models", "networks", "weights"):
            for pattern in patterns:
                hits = sorted((folder / sub).glob(pattern))
                if hits:
                    return str(hits[0])
    return None


def katago_command(paths=None, visits: int = None):
    """KataGo 를 GTP 모드로 띄우는 명령을 만든다."""
    paths = paths or find_katago()
    if not paths:
        return None
    command = [paths["실행"], "gtp"]
    if paths.get("설정"):
        command += ["-config", paths["설정"]]
    if paths.get("신경망"):
        command += ["-model", paths["신경망"]]
    if visits:
        command += ["-override-config", f"maxVisits={visits}"]
    return command


# ----------------------------------------------------------------------
# 엔진 고르기
# ----------------------------------------------------------------------
def load_engine(spec: str = "auto", think_time: float = 5.0,
                visits: int = None, seed: int = None):
    """대국 상대를 만든다.

    :param spec: ``"auto"``(KataGo 있으면 쓰고 없으면 내장 봇),
        ``"katago"``, ``"내장"``, 또는 직접 쓴 실행 명령
        (예: ``"leelaz -g -w net.gz"``).
    :param think_time: 한 수에 쓸 시간(초).
    :param visits: KataGo 탐색 수 제한. 낮출수록 약하고 빠르다.
    :return: `Player`
    """
    spec = (spec or "auto").strip()

    if spec in ("내장", "builtin", "none", "off"):
        return BuiltinBot(seed=seed)

    if spec in ("auto", "katago"):
        command = katago_command(visits=visits)
        if command:
            engine = GtpEngine(command, name="KataGo", timeout=60.0)
            try:
                return EngineBot(engine.start(), think_time, "KataGo")
            except (EngineNotFound, GtpError) as exc:
                engine.stop()
                if spec == "katago":
                    raise
                _warn(f"KataGo 를 띄우지 못해 내장 봇으로 둡니다: {exc}")
        elif spec == "katago":
            raise EngineNotFound(
                "KataGo 를 찾지 못했습니다. "
                f"설치한 뒤 {_KATAGO_ENV} 환경변수로 경로를 알려주세요."
            )
        return BuiltinBot(seed=seed)

    # 직접 쓴 명령
    import shlex
    engine = GtpEngine(shlex.split(spec), timeout=60.0)
    return EngineBot(engine.start(), think_time)


def engine_status():
    """지금 쓸 수 있는 엔진을 정리해서 돌려준다 (화면 표시용)."""
    paths = find_katago()
    return {
        "KataGo": {
            "설치됨": bool(paths),
            **(paths or {}),
            "안내": None if paths else
                    "KataGo 가 없어 내장 봇으로 둡니다. README 의 설치 안내를 보세요.",
        },
        "내장 봇": {"설치됨": True, "실력": BuiltinBot.strength},
        "절예": {
            "설치됨": False,
            "안내": "절예(Fine Art)는 텐센트 비공개 엔진이라 "
                    "내려받아 붙일 수 있는 공개 배포판이나 API 가 없습니다. "
                    "야호바둑 등 서비스 안에서만 쓸 수 있습니다.",
        },
    }


def _vertex(size: int, move):
    columns = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    row, col = move
    return f"{columns[col]}{size - row}"


def _warn(message: str):
    import sys
    print(f"[알림] {message}", file=sys.stderr)
