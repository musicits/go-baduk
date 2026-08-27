"""대국 진행·엔진 고르기 테스트."""

import pytest

from baduk.board import BLACK, WHITE, PASS, Board, IllegalMove
from baduk.engine import BuiltinBot, Player, engine_status, load_engine
from baduk.game import Game, new_game


def 새판(**kwargs):
    kwargs.setdefault("size", 9)
    kwargs.setdefault("komi", 5.5)
    kwargs.setdefault("bot", BuiltinBot(seed=7))
    return Game(**kwargs)


class 정해진봇(Player):
    """미리 정한 수만 두는 시험용 상대."""

    name = "시험봇"

    def __init__(self, 수들):
        self.수들 = list(수들)

    def genmove(self, board, color):
        return self.수들.pop(0) if self.수들 else PASS


def test_사람이_두면_엔진이_받는다():
    game = 새판(bot=정해진봇([(0, 0)]))
    game.play_human((4, 4))
    game.play_bot()
    assert game.board.get((4, 4)) == BLACK
    assert game.board.get((0, 0)) == WHITE
    assert game.board.to_play == BLACK


def test_위법한_수는_거절된다():
    game = 새판()
    game.play_human((4, 4))
    with pytest.raises(IllegalMove):
        game.play_human((4, 4))


def test_차례_판정():
    game = 새판(human=BLACK)
    assert game.human_turn() is True
    game.play_human((4, 4))
    assert game.human_turn() is False


def test_패스_두_번이면_끝나고_결과가_남는다():
    game = 새판(bot=정해진봇([PASS]))
    game.pass_turn()                  # 사람이 패스
    assert game.finished is False
    game.play_bot()                   # 엔진도 패스하면 그때 끝난다
    assert game.finished is True
    assert "승" in game.result or "무승부" in game.result


def test_돌_던지기():
    game = 새판()
    결과 = game.resign(BLACK)
    assert game.finished is True
    assert "백" in 결과 and "불계" in 결과


def test_엔진이_던지면_사람_승():
    game = 새판(bot=정해진봇(["resign"]))
    game.play_human((4, 4))
    assert game.play_bot() == "resign"
    assert game.finished is True
    assert "흑" in game.result


def test_무르기는_두_수를_되돌린다():
    game = 새판(bot=정해진봇([(0, 0)]))
    game.play_human((4, 4))
    game.play_bot()
    assert game.undo(2) == 2
    assert game.board.is_empty((4, 4))
    assert len(game.board.moves) == 0


def test_무르면_끝난_대국이_다시_열린다():
    game = 새판(bot=정해진봇([PASS]))
    game.pass_turn()
    game.play_bot()
    assert game.finished is True
    game.undo(2)
    assert game.finished is False
    assert game.result is None


def test_접바둑은_백이_먼저():
    game = 새판(size=19, komi=0.5, handicap=4)
    assert game.board.to_play == WHITE
    assert game.board.handicap == 4
    assert sum(1 for s in game.board.stones if s == BLACK) == 4


def test_접바둑이면_덤이_줄어든다():
    game = Game(size=19, handicap=4, bot=BuiltinBot(seed=1))
    assert game.board.komi == 0.5


def test_판_크기별_기본_덤():
    assert Game(size=19, bot=BuiltinBot()).board.komi == 6.5
    assert Game(size=9, bot=BuiltinBot()).board.komi == 5.5


def test_상태_딕셔너리():
    game = 새판(bot=정해진봇([(0, 0)]))
    game.play_human((4, 4))
    상태 = game.state()
    assert 상태["크기"] == 9
    assert 상태["수순"] == 1
    assert 상태["마지막수"] == [4, 4]
    assert 상태["차례"] == WHITE
    assert 상태["끝남"] is False
    assert len(상태["돌"]) == 81


def test_기보를_뽑는다():
    game = 새판()
    game.play_human((4, 4))
    글 = game.sgf()
    assert "SZ[9]" in 글
    assert ";B[ee]" in 글


def test_계가():
    game = 새판()
    점수 = game.score(dead=[])
    assert 점수["규칙"] == "중국"
    assert "결과" in 점수


def test_일본식으로도_계가한다():
    game = 새판(rules="일본")
    assert game.score(dead=[])["규칙"] == "일본"


def test_분석을_못_하는_봇은_빈_목록():
    game = 새판()
    assert game.analyze() == []


# ---------------------------------------------------------------------
# 내장 봇
# ---------------------------------------------------------------------
def test_내장봇은_합법수만_둔다():
    board = Board(9)
    bot = BuiltinBot(seed=3)
    for _ in range(40):
        move = bot.genmove(board, board.to_play)
        if move is PASS:
            break
        assert board.is_legal(move, board.to_play), f"위법한 수: {move}"
        board.play(move)
        bot.observe(board.moves[-1][0], move)


def test_내장봇은_따낼_수_있으면_따낸다():
    board = Board(9)
    # 백 한 점이 활로 하나(4,4)만 남았다.
    board.stones[board.index((4, 5))] = WHITE
    for point in [(3, 5), (5, 5), (4, 6)]:
        board.stones[board.index(point)] = BLACK
    board.to_play = BLACK
    board._seen = {board._position_key()}
    assert BuiltinBot(seed=1).genmove(board, BLACK) == (4, 4)


def test_내장봇은_자기_눈을_안_메운다():
    board = Board(9)
    # 가운데에 흑의 눈 하나를 만든다.
    for point in [(3, 4), (5, 4), (4, 3), (4, 5),
                  (3, 3), (3, 5), (5, 3), (5, 5)]:
        board.stones[board.index(point)] = BLACK
    board.to_play = BLACK
    board._seen = {board._position_key()}
    수 = BuiltinBot(seed=2).genmove(board, BLACK)
    assert 수 != (4, 4)


def test_내장봇은_둘_데가_없으면_패스():
    board = Board(9)
    for idx in range(81):
        board.stones[idx] = BLACK
    board.stones[board.index((4, 4))] = 0     # 자기 눈 하나만 비어 있다
    board.to_play = BLACK
    assert BuiltinBot(seed=1).genmove(board, BLACK) is PASS


def test_같은_씨앗이면_같은_수():
    board = Board(9)
    assert (BuiltinBot(seed=42).genmove(board, BLACK)
            == BuiltinBot(seed=42).genmove(board, BLACK))


# ---------------------------------------------------------------------
# 엔진 고르기
# ---------------------------------------------------------------------
def test_내장을_고르면_내장봇():
    assert isinstance(load_engine("내장"), BuiltinBot)


def test_KataGo가_없으면_내장봇으로_물러난다(monkeypatch):
    monkeypatch.setattr("baduk.engine.katago_command", lambda **kw: None)
    assert isinstance(load_engine("auto"), BuiltinBot)


def test_KataGo를_콕_집었는데_없으면_알려준다(monkeypatch):
    from baduk.gtp import EngineNotFound
    monkeypatch.setattr("baduk.engine.katago_command", lambda **kw: None)
    with pytest.raises(EngineNotFound, match="KataGo"):
        load_engine("katago")


def test_엔진_현황에는_절예_안내가_들어간다():
    현황 = engine_status()
    assert 현황["내장 봇"]["설치됨"] is True
    assert 현황["절예"]["설치됨"] is False
    assert "공개" in 현황["절예"]["안내"]


def test_새_대국_만들기():
    game = new_game(size=9, engine="내장", komi=5.5)
    assert game.board.size == 9
    assert isinstance(game.bot, BuiltinBot)
    game.close()
