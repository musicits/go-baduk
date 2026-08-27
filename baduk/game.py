"""대국 진행 관리.

판(`Board`)과 대국자(`Player`)를 묶어서 한 판을 끝까지 진행시킨다.
터미널이든 웹이든 이 클래스를 공통으로 쓴다.
"""

from __future__ import annotations

from .board import BLACK, WHITE, PASS, Board, color_name, opponent, IllegalMove
from .engine import BuiltinBot, EngineBot, Player, load_engine
from .sgf import to_sgf


class Game:
    """한 판의 상태를 들고 있는다.

    :param size: 판 크기.
    :param komi: 덤.
    :param handicap: 접바둑 치석 수 (0 이면 맞바둑).
    :param human: 사람이 잡을 색. 둘 다 엔진이면 None.
    :param bot: 상대 `Player`. None 이면 내장 봇.
    :param rules: 계가 방식 (``"중국"`` 또는 ``"한국"``).
    """

    def __init__(self, size: int = 19, komi: float = None, handicap: int = 0,
                 human: int = BLACK, bot: Player = None, rules: str = "중국"):
        if komi is None:
            komi = 0.5 if handicap else (6.5 if size >= 19 else 5.5)
        self.board = Board(size, komi)
        self.rules = rules
        self.human = human
        self.bot = bot if bot is not None else BuiltinBot()
        self.finished = False
        self.result = None
        self.resigned_by = None
        self.last_analysis = []

        if handicap >= 2:
            self.board.place_handicap(handicap)
        self.bot.setup(self.board)

    # ------------------------------------------------------------------
    @property
    def to_play(self) -> int:
        """이번에 둘 색."""
        return self.board.to_play

    @property
    def bot_color(self):
        """엔진이 잡은 색."""
        return None if self.human is None else opponent(self.human)

    def human_turn(self) -> bool:
        """지금이 사람 차례인지."""
        return not self.finished and self.human is not None and self.to_play == self.human

    # ------------------------------------------------------------------
    def play_human(self, move):
        """사람의 수를 둔다. 위법하면 `IllegalMove`."""
        if self.finished:
            raise IllegalMove("이미 끝난 대국입니다")
        color = self.to_play
        self.board.play(move, color)
        self.bot.observe(color, move)
        self._check_end()
        return move

    def play_bot(self):
        """엔진에게 한 수 두게 한다. 둔 수를 돌려준다."""
        if self.finished:
            return None
        color = self.to_play
        move = self.bot.genmove(self.board, color)
        if move == "resign":
            self.finished = True
            self.resigned_by = color
            self.result = f"{color_name(opponent(color))} 불계승"
            return "resign"
        self.board.play(move, color)
        self._check_end()
        return move

    def pass_turn(self):
        """패스한다."""
        return self.play_human(PASS)

    def resign(self, color: int = None):
        """돌을 던진다."""
        color = self.to_play if color is None else color
        self.finished = True
        self.resigned_by = color
        self.result = f"{color_name(opponent(color))} 불계승"
        return self.result

    def undo(self, count: int = 2) -> int:
        """무른다. 사람과 엔진의 수를 짝지어 되돌리려고 기본이 2 다.

        :return: 실제로 무른 수.
        """
        done = 0
        for _ in range(count):
            if not self.board.undo():
                break
            done += 1
        if done:
            self.finished = False
            self.result = None
            self.resigned_by = None
            for _ in range(done):
                try:
                    if isinstance(self.bot, EngineBot):
                        self.bot.engine.undo()
                except Exception:
                    break
        return done

    def analyze(self):
        """지금 국면의 승률을 본다 (KataGo 등에서만)."""
        self.last_analysis = self.bot.analyze(self.board, self.to_play)
        return self.last_analysis

    # ------------------------------------------------------------------
    def dead_stones(self):
        """죽은 돌 자리. 엔진이 알려주면 그걸 쓰고, 못 하면 빈 목록."""
        if isinstance(self.bot, EngineBot):
            try:
                return self.bot.dead_stones(self.board)
            except Exception:
                return []
        return []

    def score(self, dead=None):
        """집을 센다."""
        dead = self.dead_stones() if dead is None else dead
        return self.board.score(dead, rules=self.rules)

    def sgf(self, black: str = None, white: str = None) -> str:
        """기보를 SGF 로 뽑는다."""
        names = self._names()
        return to_sgf(
            self.board,
            black=black or names[BLACK],
            white=white or names[WHITE],
            result=self.result,
        )

    def state(self):
        """화면에 뿌릴 상태를 딕셔너리로 만든다."""
        board = self.board
        last = None
        for _, move in reversed(board.moves):
            if move is not PASS:
                last = move
                break
        return {
            "크기": board.size,
            "돌": board.stones,
            "차례": board.to_play,
            "덤": board.komi,
            "따낸돌": {"흑": board.captures[BLACK], "백": board.captures[WHITE]},
            "수순": len(board.moves),
            "마지막수": list(last) if last else None,
            "패": list(board.coord(board.ko)) if board.ko is not None else None,
            "끝남": self.finished,
            "결과": self.result,
            "사람": self.human,
            "엔진이름": self.bot.name,
            "엔진실력": self.bot.strength,
            "분석": self.last_analysis,
            "규칙": self.rules,
        }

    def close(self):
        """엔진을 정리한다."""
        self.bot.close()

    # ------------------------------------------------------------------
    def _check_end(self):
        if self.board.is_game_over():
            self.finished = True
            self.result = self.score()["결과"]

    def _names(self):
        engine = self.bot.name
        if self.human is None:
            return {BLACK: engine, WHITE: engine}
        return {
            self.human: "사람",
            opponent(self.human): engine,
        }


def new_game(size: int = 19, engine: str = "auto", handicap: int = 0,
             human: int = BLACK, komi: float = None, think_time: float = 5.0,
             visits: int = None, rules: str = "중국") -> Game:
    """엔진까지 챙겨서 새 대국을 시작한다."""
    bot = load_engine(engine, think_time=think_time, visits=visits)
    return Game(size=size, komi=komi, handicap=handicap, human=human,
                bot=bot, rules=rules)
