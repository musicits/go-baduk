"""SGF 기보 읽기·쓰기.

SGF 는 바둑 기보의 표준 형식이라 다른 프로그램(사바키·리지·야호바둑 등)과
기보를 주고받을 수 있다. 여기서는 대국 저장·불러오기에 필요한 만큼만 다룬다.
"""

from __future__ import annotations

import re
from datetime import date

from .board import BLACK, WHITE, EMPTY, PASS, Board

_LETTERS = "abcdefghijklmnopqrstuvwxyz"
_PROPERTY = re.compile(r"([A-Z]+)((?:\s*\[(?:\\.|[^\]\\])*\])+)", re.S)
_VALUE = re.compile(r"\[((?:\\.|[^\]\\])*)\]", re.S)


def to_sgf(board: Board, black: str = "흑", white: str = "백",
           result: str = None, game_name: str = None) -> str:
    """판의 착수 이력을 SGF 문자열로 만든다."""
    parts = [
        "GM[1]",                       # 1 = 바둑
        "FF[4]",
        "CA[UTF-8]",
        "AP[baduk-py]",
        f"SZ[{board.size}]",
        f"KM[{board.komi}]",
        f"PB[{_escape(black)}]",
        f"PW[{_escape(white)}]",
        f"DT[{date.today().isoformat()}]",
    ]
    if board.handicap:
        parts.append(f"HA[{board.handicap}]")
    if game_name:
        parts.append(f"GN[{_escape(game_name)}]")
    if result:
        parts.append(f"RE[{_escape(result)}]")

    # 치석은 착수가 아니라 미리 놓인 돌(AB)로 적는다.
    if board.handicap:
        placed = [
            board.coord(i) for i, s in enumerate(board.stones) if s == BLACK
        ]
        played = {m for c, m in board.moves if m is not PASS and c == BLACK}
        setup = [p for p in placed if p not in played][: board.handicap]
        if setup:
            parts.append("AB" + "".join(f"[{_point(p)}]" for p in setup))

    body = "".join(
        f";{'B' if color == BLACK else 'W'}[{_point(move)}]"
        for color, move in board.moves
    )
    return "(;" + "".join(parts) + body + ")"


def save_sgf(path, board: Board, **kwargs) -> str:
    """SGF 파일로 저장하고 경로를 돌려준다."""
    text = to_sgf(board, **kwargs)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return str(path)


def from_sgf(text: str) -> Board:
    """SGF 문자열을 읽어 그 시점까지 둔 판을 만든다.

    변화도(분기)는 첫 갈래만 따라간다.
    """
    text = text.strip()
    if not text.startswith("("):
        raise ValueError("SGF 형식이 아닙니다")
    text = _first_branch(text)

    nodes = [n for n in text.split(";") if n.strip()]
    if not nodes:
        raise ValueError("SGF 에 내용이 없습니다")

    header = dict(_properties(nodes[0]))
    size = int(header.get("SZ", ["19"])[0].split(":")[0])
    komi = float(header.get("KM", ["6.5"])[0] or 6.5)
    board = Board(size, komi)

    for color_key, stone in (("AB", BLACK), ("AW", WHITE)):
        for value in header.get(color_key, []):
            point = _parse_point(value, size)
            if point is not PASS:
                board.stones[board.index(point)] = stone
    if header.get("AB"):
        board.handicap = len(header["AB"])
        board.to_play = WHITE
        board._seen = {board._position_key()}

    for node in nodes[1:]:
        props = dict(_properties(node))
        for key, color in (("B", BLACK), ("W", WHITE)):
            if key not in props:
                continue
            point = _parse_point(props[key][0], size)
            board.play(point, color)
    return board


def load_sgf(path) -> Board:
    """SGF 파일을 읽는다."""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return from_sgf(handle.read())


# ----------------------------------------------------------------------
def _point(move) -> str:
    if move is PASS:
        return ""
    row, col = move
    return _LETTERS[col] + _LETTERS[row]


def _parse_point(value: str, size: int):
    value = value.strip()
    # 빈 값과 tt(옛 방식)는 패스다.
    if len(value) < 2 or (value == "tt" and size <= 19):
        return PASS
    col = _LETTERS.find(value[0])
    row = _LETTERS.find(value[1])
    if col < 0 or row < 0 or col >= size or row >= size:
        return PASS
    return (row, col)


def _properties(node: str):
    for match in _PROPERTY.finditer(node):
        key = match.group(1)
        values = [_unescape(v) for v in _VALUE.findall(match.group(2))]
        yield key, values


def _first_branch(text: str) -> str:
    """분기가 나오면 첫 갈래만 남긴다."""
    depth = 0
    out = []
    for i, char in enumerate(text):
        if char == "(":
            depth += 1
            if depth > 1:
                # 두 번째 이후 갈래는 통째로 버린다.
                nested = 0
                for j in range(i, len(text)):
                    if text[j] == "(":
                        nested += 1
                    elif text[j] == ")":
                        nested -= 1
                        if nested == 0:
                            return "".join(out) + text[j + 1:].split(")")[0]
                break
            continue
        if char == ")":
            depth -= 1
            if depth == 0:
                break
            continue
        out.append(char)
    return "".join(out)


def _escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("]", "\\]")


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)
