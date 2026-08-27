"""바둑 규칙 엔진.

돌 놓기·따내기·자살수 금지·패(ko)·집 계산을 담당한다.
외부 의존성 없이 순수 파이썬으로만 동작한다.

좌표는 `(row, col)` 튜플이며 좌상단이 `(0, 0)` 이다.
패스는 `PASS` (None) 로 나타낸다.
"""

from __future__ import annotations

EMPTY = 0
BLACK = 1
WHITE = 2

PASS = None

_NAMES = {BLACK: "흑", WHITE: "백", EMPTY: "빈칸"}

# GTP 좌표에는 I 를 쓰지 않는다 (1 과 헷갈려서).
_COLUMNS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


def opponent(color: int) -> int:
    """상대 색을 돌려준다."""
    return WHITE if color == BLACK else BLACK


def color_name(color: int) -> str:
    """색 이름을 한국어로 돌려준다."""
    return _NAMES.get(color, "?")


class IllegalMove(Exception):
    """규칙에 어긋나는 수를 두려 할 때 발생한다."""


class Board:
    """바둑판 하나. 착수 이력을 들고 있어서 무르기(undo)가 된다.

    :param size: 판 크기 (9, 13, 19 …)
    :param komi: 덤. 백에게 더해지는 집.
    :param superko: True 면 동형반복 전체 금지(positional superko),
        False 면 직전 한 수 되따내기(단수패)만 금지한다.
    """

    def __init__(self, size: int = 19, komi: float = 6.5, superko: bool = True):
        if size < 2 or size > 25:
            raise ValueError("판 크기는 2~25 사이여야 합니다")
        self.size = size
        self.komi = komi
        self.superko = superko
        self.stones = [EMPTY] * (size * size)
        self.captures = {BLACK: 0, WHITE: 0}
        self.to_play = BLACK
        self.ko = None            # 단수패로 막힌 자리 (index)
        self.moves = []           # [(color, move), ...]
        self.handicap = 0
        self._neighbors = _build_neighbors(size)
        self._undo_stack = []
        self._seen = {self._position_key()}

    # ------------------------------------------------------------------
    # 좌표 변환
    # ------------------------------------------------------------------
    def index(self, move) -> int:
        """`(row, col)` 을 내부 인덱스로 바꾼다."""
        row, col = move
        if not (0 <= row < self.size and 0 <= col < self.size):
            raise IllegalMove(f"판 밖입니다: {move}")
        return row * self.size + col

    def coord(self, idx: int):
        """내부 인덱스를 `(row, col)` 로 바꾼다."""
        return divmod(idx, self.size)

    def to_gtp(self, move) -> str:
        """`(row, col)` 을 GTP 좌표 문자열(예: ``Q16``)로 바꾼다."""
        if move is PASS:
            return "pass"
        row, col = move
        return f"{_COLUMNS[col]}{self.size - row}"

    def from_gtp(self, text: str):
        """GTP 좌표 문자열을 `(row, col)` 로 바꾼다. ``pass`` 는 `PASS`."""
        text = text.strip().upper()
        if text in ("PASS", "PS"):
            return PASS
        if text == "RESIGN":
            raise ValueError("착수 좌표가 아닙니다: resign")
        col = _COLUMNS.find(text[0])
        if col < 0:
            raise ValueError(f"좌표를 알 수 없습니다: {text}")
        try:
            number = int(text[1:])
        except ValueError:
            raise ValueError(f"좌표를 알 수 없습니다: {text}") from None
        row = self.size - number
        if not (0 <= row < self.size and col < self.size):
            raise ValueError(f"판 밖입니다: {text}")
        return (row, col)

    # ------------------------------------------------------------------
    # 판 읽기
    # ------------------------------------------------------------------
    def get(self, move) -> int:
        """그 자리의 돌 색을 돌려준다."""
        return self.stones[self.index(move)]

    def is_empty(self, move) -> bool:
        """빈 자리인지 확인한다."""
        return self.get(move) == EMPTY

    def group(self, move):
        """그 돌이 속한 단위(연결된 돌)와 활로를 돌려준다.

        :return: ``(돌 인덱스 집합, 활로 인덱스 집합)``
        """
        idx = self.index(move)
        if self.stones[idx] == EMPTY:
            return set(), set()
        return self._group_at(idx)

    def liberties(self, move) -> int:
        """그 돌이 속한 단위의 활로 수."""
        return len(self.group(move)[1])

    def legal_moves(self, color: int = None):
        """지금 둘 수 있는 모든 자리를 돌려준다 (패스 제외)."""
        color = self.to_play if color is None else color
        out = []
        for idx in range(len(self.stones)):
            if self.stones[idx] != EMPTY:
                continue
            move = self.coord(idx)
            if self.is_legal(move, color):
                out.append(move)
        return out

    def is_legal(self, move, color: int = None) -> bool:
        """그 수가 합법인지 확인한다. 예외를 던지지 않는다."""
        if move is PASS:
            return True
        try:
            self._check(move, self.to_play if color is None else color)
        except IllegalMove:
            return False
        return True

    def illegal_reason(self, move, color: int = None):
        """합법이면 None, 아니면 사유 문자열을 돌려준다."""
        if move is PASS:
            return None
        try:
            self._check(move, self.to_play if color is None else color)
        except IllegalMove as exc:
            return str(exc)
        return None

    # ------------------------------------------------------------------
    # 착수
    # ------------------------------------------------------------------
    def play(self, move, color: int = None) -> int:
        """한 수 둔다. 따낸 돌 수를 돌려준다.

        규칙에 어긋나면 `IllegalMove` 를 던지고 판은 그대로 둔다.
        """
        color = self.to_play if color is None else color
        snapshot = (
            list(self.stones), dict(self.captures), self.to_play,
            self.ko, len(self.moves), set(self._seen),
        )

        if move is PASS:
            self._undo_stack.append(snapshot)
            self.ko = None
            self.moves.append((color, PASS))
            self.to_play = opponent(color)
            return 0

        captured = self._check(move, color)
        idx = self.index(move)

        self._undo_stack.append(snapshot)
        self.stones[idx] = color
        for dead in captured:
            self.stones[dead] = EMPTY
        self.captures[color] += len(captured)

        # 단 한 점만 따냈고 내 돌도 한 점 단수면 그 자리가 패다.
        self.ko = None
        if len(captured) == 1:
            mine, libs = self._group_at(idx)
            if len(mine) == 1 and len(libs) == 1:
                self.ko = next(iter(captured))

        self.moves.append((color, move))
        self.to_play = opponent(color)
        self._seen.add(self._position_key())
        return len(captured)

    def undo(self) -> bool:
        """한 수 무른다. 무를 수가 없으면 False."""
        if not self._undo_stack:
            return False
        stones, captures, to_play, ko, move_count, seen = self._undo_stack.pop()
        self.stones = stones
        self.captures = captures
        self.to_play = to_play
        self.ko = ko
        del self.moves[move_count:]
        self._seen = seen
        return True

    def place_handicap(self, count: int):
        """접바둑 치석을 놓는다. 놓은 자리 목록을 돌려준다.

        치석을 놓으면 백이 먼저 둔다.
        """
        points = handicap_points(self.size, count)
        for point in points:
            self.stones[self.index(point)] = BLACK
        if points:
            self.handicap = len(points)
            self.to_play = WHITE
            self._undo_stack.clear()
            self._seen = {self._position_key()}
        return points

    def is_game_over(self) -> bool:
        """연속 두 번 패스로 끝났는지 확인한다."""
        return (
            len(self.moves) >= 2
            and self.moves[-1][1] is PASS
            and self.moves[-2][1] is PASS
        )

    # ------------------------------------------------------------------
    # 집 계산
    # ------------------------------------------------------------------
    def territory(self, dead=()):
        """빈 자리의 주인을 가린다.

        :param dead: 죽은 돌로 칠 자리 목록. 그 돌은 없는 셈 치고 센다.
        :return: ``{BLACK: 집 수, WHITE: 집 수, "중립": 공배 수}``
        """
        stones = list(self.stones)
        dead_by = {BLACK: 0, WHITE: 0}
        for point in dead:
            idx = self.index(point)
            if stones[idx] != EMPTY:
                dead_by[stones[idx]] += 1
                stones[idx] = EMPTY

        counts = {BLACK: 0, WHITE: 0, "중립": 0}
        visited = [False] * len(stones)
        for start in range(len(stones)):
            if stones[start] != EMPTY or visited[start]:
                continue
            region, borders = [], set()
            stack = [start]
            visited[start] = True
            while stack:
                i = stack.pop()
                region.append(i)
                for j in self._neighbors[i]:
                    if stones[j] == EMPTY:
                        if not visited[j]:
                            visited[j] = True
                            stack.append(j)
                    else:
                        borders.add(stones[j])
            if len(borders) == 1:
                counts[borders.pop()] += len(region)
            else:
                counts["중립"] += len(region)
        counts["사석"] = dead_by
        return counts

    def score(self, dead=(), rules: str = "중국"):
        """집을 세어 결과를 돌려준다.

        :param dead: 죽은 돌로 칠 자리 목록.
        :param rules: ``"중국"``(계가: 돌+집) 또는 ``"일본"``(집+사석).
        :return: 점수 딕셔너리. ``"차이"`` 가 양수면 흑 우세.
        """
        counts = self.territory(dead)
        dead_set = {self.index(p) for p in dead}
        dead_by = counts["사석"]

        if rules == "중국":
            alive = {BLACK: 0, WHITE: 0}
            for idx, stone in enumerate(self.stones):
                if stone != EMPTY and idx not in dead_set:
                    alive[stone] += 1
            black = counts[BLACK] + alive[BLACK]
            white = counts[WHITE] + alive[WHITE] + self.komi
        elif rules == "일본":
            black = counts[BLACK] + self.captures[BLACK] + dead_by[WHITE]
            white = counts[WHITE] + self.captures[WHITE] + dead_by[BLACK] + self.komi
        else:
            raise ValueError(f"모르는 규칙입니다: {rules}")

        diff = black - white
        if diff > 0:
            result = f"흑 {_fmt(diff)}집 승"
        elif diff < 0:
            result = f"백 {_fmt(-diff)}집 승"
        else:
            result = "무승부"
        return {
            "규칙": rules,
            "흑": black,
            "백": white,
            "차이": diff,
            "결과": result,
            "덤": self.komi,
            "공배": counts["중립"],
        }

    # ------------------------------------------------------------------
    # 표시
    # ------------------------------------------------------------------
    def ascii(self, marks=None) -> str:
        """판을 글자로 그린다. `marks` 는 ``{(row, col): "글자"}``."""
        marks = marks or {}
        stars = set(star_points(self.size))
        width = len(str(self.size))
        lines = ["   " + " ".join(_COLUMNS[: self.size])]
        for row in range(self.size):
            cells = []
            for col in range(self.size):
                if (row, col) in marks:
                    cells.append(marks[(row, col)])
                    continue
                stone = self.stones[row * self.size + col]
                if stone == BLACK:
                    cells.append("●")
                elif stone == WHITE:
                    cells.append("○")
                elif (row, col) in stars:
                    cells.append("+")
                else:
                    cells.append(".")
            number = str(self.size - row).rjust(width)
            lines.append(f"{number} " + " ".join(cells) + f" {number}")
        lines.append("   " + " ".join(_COLUMNS[: self.size]))
        return "\n".join(lines)

    def copy(self) -> "Board":
        """같은 상태의 새 판을 만든다 (착수 이력은 복사하지 않는다)."""
        other = Board(self.size, self.komi, self.superko)
        other.stones = list(self.stones)
        other.captures = dict(self.captures)
        other.to_play = self.to_play
        other.ko = self.ko
        other.moves = list(self.moves)
        other.handicap = self.handicap
        other._seen = set(self._seen)
        return other

    def __str__(self) -> str:
        return self.ascii()

    # ------------------------------------------------------------------
    # 내부
    # ------------------------------------------------------------------
    def _check(self, move, color: int):
        """합법성을 확인하고 따낼 돌 집합을 돌려준다."""
        idx = self.index(move)
        if self.stones[idx] != EMPTY:
            raise IllegalMove("이미 돌이 있습니다")
        if idx == self.ko:
            raise IllegalMove("패입니다 — 다른 곳을 먼저 두세요")

        enemy = opponent(color)
        captured = set()
        for j in self._neighbors[idx]:
            if self.stones[j] != enemy or j in captured:
                continue
            group, libs = self._group_at(j)
            if libs == {idx}:
                captured |= group

        if not captured:
            # 따낼 게 없으면 내 돌이 살아남는지 본다.
            self.stones[idx] = color
            try:
                _, libs = self._group_at(idx)
                if not libs:
                    raise IllegalMove("자살수입니다")
            finally:
                self.stones[idx] = EMPTY

        if self.superko:
            self.stones[idx] = color
            for dead in captured:
                self.stones[dead] = EMPTY
            key = (opponent(color),) + tuple(self.stones)
            repeated = key in self._seen
            self.stones[idx] = EMPTY
            for dead in captured:
                self.stones[dead] = enemy
            if repeated:
                raise IllegalMove("같은 판이 반복됩니다 (동형반복 금지)")

        return captured

    def _group_at(self, idx: int):
        color = self.stones[idx]
        stack = [idx]
        group = {idx}
        libs = set()
        while stack:
            i = stack.pop()
            for j in self._neighbors[i]:
                stone = self.stones[j]
                if stone == EMPTY:
                    libs.add(j)
                elif stone == color and j not in group:
                    group.add(j)
                    stack.append(j)
        return group, libs

    def _position_key(self):
        return (self.to_play,) + tuple(self.stones)


def _build_neighbors(size: int):
    table = []
    for idx in range(size * size):
        row, col = divmod(idx, size)
        near = []
        if row > 0:
            near.append(idx - size)
        if row < size - 1:
            near.append(idx + size)
        if col > 0:
            near.append(idx - 1)
        if col < size - 1:
            near.append(idx + 1)
        table.append(tuple(near))
    return table


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def star_points(size: int):
    """화점 좌표 목록."""
    if size < 7:
        return []
    edge = 3 if size >= 13 else 2
    middle = size // 2
    far = size - 1 - edge
    points = [(r, c) for r in (edge, far) for c in (edge, far)]
    if size % 2 == 1 and size >= 9:
        points += [(middle, middle), (edge, middle), (far, middle),
                   (middle, edge), (middle, far)]
        if size < 13:
            points = [(edge, edge), (edge, far), (far, edge), (far, far),
                      (middle, middle)]
    return sorted(set(points))


def handicap_points(size: int, count: int):
    """접바둑 치석 자리. 2~9 점을 지원한다."""
    if count < 2:
        return []
    if size < 9 or size % 2 == 0:
        raise ValueError("접바둑은 9·13·19 로만 둘 수 있습니다")
    edge = 3 if size >= 13 else 2
    middle = size // 2
    far = size - 1 - edge
    corners = [(far, far), (edge, edge), (edge, far), (far, edge)]
    sides = [(middle, edge), (middle, far), (far, middle), (edge, middle)]
    center = (middle, middle)

    count = min(count, 9)
    if count <= 4:
        return corners[:count]
    points = list(corners)
    if count in (5, 7, 9):
        points.append(center)
    extra = count - len(points)
    points += sides[:extra]
    return points
