"""바둑 규칙 엔진 테스트."""

import pytest

from baduk.board import (
    BLACK, WHITE, EMPTY, PASS, Board, IllegalMove,
    handicap_points, opponent, star_points,
)


def place(board, moves, color=BLACK):
    """색을 번갈지 않고 한 색으로만 돌을 놓는다 (모양 만들기용)."""
    for move in moves:
        board.stones[board.index(move)] = color


def test_좌표_변환은_I를_건너뛴다():
    board = Board(19)
    assert board.to_gtp((3, 3)) == "D16"
    assert board.from_gtp("D16") == (3, 3)
    # H 다음은 I 가 아니라 J 다.
    assert board.to_gtp((0, 8)) == "J19"
    assert board.from_gtp("J19") == (0, 8)
    assert board.from_gtp("pass") is PASS


def test_좌표가_판_밖이면_거절한다():
    board = Board(9)
    with pytest.raises(ValueError):
        board.from_gtp("T1")
    with pytest.raises(ValueError):
        board.from_gtp("가나")


def test_한_점_따내기():
    board = Board(9)
    board.play((1, 0), BLACK)
    board.play((0, 0), WHITE)
    board.play((0, 1), BLACK)
    assert board.get((0, 0)) == EMPTY
    assert board.captures[BLACK] == 1


def test_여러_점_한꺼번에_따내기():
    board = Board(9)
    # 귀의 백 두 점. 활로는 (0,2) · (1,0) · (1,1) 셋뿐이다.
    place(board, [(0, 0), (0, 1)], WHITE)
    place(board, [(1, 0), (1, 1)], BLACK)
    board.to_play = BLACK
    board._seen = {board._position_key()}

    board.play((0, 2), BLACK)          # 마지막 활로를 메운다
    assert board.get((0, 0)) == EMPTY
    assert board.get((0, 1)) == EMPTY
    assert board.captures[BLACK] == 2


def test_자살수는_둘_수_없다():
    board = Board(9)
    place(board, [(0, 1), (1, 0)], WHITE)
    board.to_play = BLACK
    with pytest.raises(IllegalMove, match="자살수"):
        board.play((0, 0), BLACK)
    assert board.illegal_reason((0, 0), BLACK) is not None
    assert not board.is_legal((0, 0), BLACK)


def test_따내면서_두면_자살수가_아니다():
    board = Board(9)
    # 백 한 점이 흑에 둘러싸여 활로가 (0,0) 하나만 남은 모양.
    place(board, [(0, 1)], WHITE)
    place(board, [(1, 1), (0, 2)], BLACK)
    board.to_play = BLACK
    board.play((0, 0), BLACK)
    assert board.get((0, 1)) == EMPTY
    assert board.captures[BLACK] == 1


def test_이미_돌이_있으면_못_둔다():
    board = Board(9)
    board.play((4, 4), BLACK)
    with pytest.raises(IllegalMove, match="이미 돌이"):
        board.play((4, 4), WHITE)


def test_단수패_금지():
    board = Board(5)
    #    A B C D E
    #  5 . ● ○ . .
    #  4 ● ○ ㉠ ○ .      ㉠ 자리에 흑이 두면 C4 백 한 점을 따낸다
    #  3 . ● ○ . .
    place(board, [(0, 1), (1, 0), (2, 1)], BLACK)
    place(board, [(0, 2), (1, 1), (1, 3), (2, 2)], WHITE)
    board.to_play = BLACK
    board._seen = {board._position_key()}

    board.play((1, 2), BLACK)                 # 백 한 점을 따낸다
    assert board.get((1, 1)) == EMPTY
    assert board.captures[BLACK] == 1
    assert board.ko == board.index((1, 1))    # 되따내기가 막힌다

    with pytest.raises(IllegalMove, match="패"):
        board.play((1, 1), WHITE)

    board.play((4, 4), WHITE)                 # 팻감
    board.play((4, 0), BLACK)                 # 받아줌
    board.play((1, 1), WHITE)                 # 한 수 쉬었으니 이제 된다
    assert board.get((1, 1)) == WHITE
    assert board.get((1, 2)) == EMPTY         # 흑 한 점이 되따였다


def test_동형반복_금지():
    board = Board(5, superko=True)
    key = board._position_key()
    assert key in board._seen


def test_무르기():
    board = Board(9)
    board.play((2, 2), BLACK)
    board.play((3, 3), WHITE)
    before = list(board.stones)
    board.play((4, 4), BLACK)
    assert board.undo() is True
    assert board.stones == before
    assert board.to_play == BLACK
    assert len(board.moves) == 2


def test_무를_수_없으면_False():
    board = Board(9)
    assert board.undo() is False


def test_무르기로_따낸_돌도_되살아난다():
    board = Board(9)
    board.play((1, 0), BLACK)
    board.play((0, 0), WHITE)
    board.play((0, 1), BLACK)
    assert board.captures[BLACK] == 1
    board.undo()
    assert board.get((0, 0)) == WHITE
    assert board.captures[BLACK] == 0


def test_패스_두_번이면_끝난다():
    board = Board(9)
    board.play(PASS, BLACK)
    assert not board.is_game_over()
    board.play(PASS, WHITE)
    assert board.is_game_over()


def test_활로_세기():
    board = Board(9)
    board.play((4, 4), BLACK)
    assert board.liberties((4, 4)) == 4
    board2 = Board(9)
    board2.play((0, 0), BLACK)
    assert board2.liberties((0, 0)) == 2


def test_단위는_연결된_돌을_모은다():
    board = Board(9)
    place(board, [(4, 4), (4, 5), (4, 6)], BLACK)
    group, libs = board.group((4, 5))
    assert len(group) == 3
    assert len(libs) == 8


def test_집계산_중국식():
    board = Board(5, komi=0.5)
    # 왼쪽 두 줄은 흑, 오른쪽 두 줄은 백, 가운데 줄은 비움.
    place(board, [(r, c) for r in range(5) for c in (0, 1)], BLACK)
    place(board, [(r, c) for r in range(5) for c in (3, 4)], WHITE)
    점수 = board.score(rules="중국")
    assert 점수["흑"] == 10
    assert 점수["백"] == 10.5
    assert 점수["공배"] == 5


def test_집계산_일본식():
    board = Board(5, komi=0.5)
    #  흑이 B 줄, 백이 D 줄을 차지하면
    #  A 줄은 흑 집, E 줄은 백 집, C 줄은 양쪽이 맞닿아 공배다.
    place(board, [(r, 1) for r in range(5)], BLACK)
    place(board, [(r, 3) for r in range(5)], WHITE)
    점수 = board.score(rules="일본")
    assert 점수["흑"] == 5
    assert 점수["백"] == 5.5
    assert 점수["공배"] == 5


def test_죽은_돌을_빼고_센다():
    board = Board(5, komi=0.5)
    place(board, [(r, c) for r in range(5) for c in (0, 1, 2, 3)], BLACK)
    place(board, [(0, 4)], WHITE)
    살아있을때 = board.score(rules="중국")
    죽었을때 = board.score(dead=[(0, 4)], rules="중국")
    assert 죽었을때["흑"] > 살아있을때["흑"]


def test_모르는_규칙은_거절한다():
    with pytest.raises(ValueError):
        Board(9).score(rules="한국")


def test_접바둑_치석():
    board = Board(19)
    points = board.place_handicap(4)
    assert len(points) == 4
    assert all(board.get(p) == BLACK for p in points)
    assert board.to_play == WHITE          # 접바둑은 백이 먼저
    assert board.handicap == 4


def test_접바둑_점수별_자리():
    assert len(handicap_points(19, 2)) == 2
    assert len(handicap_points(19, 9)) == 9
    assert handicap_points(19, 1) == []
    assert len(set(handicap_points(19, 9))) == 9
    with pytest.raises(ValueError):
        handicap_points(8, 4)


def test_판_크기_제한():
    with pytest.raises(ValueError):
        Board(1)
    with pytest.raises(ValueError):
        Board(30)


def test_합법수_목록은_빈자리만_준다():
    board = Board(5)
    board.play((2, 2), BLACK)
    moves = board.legal_moves(WHITE)
    assert (2, 2) not in moves
    assert len(moves) == 24


def test_화점():
    assert (3, 3) in star_points(19)
    assert (9, 9) in star_points(19)
    assert len(star_points(19)) == 9
    assert star_points(5) == []


def test_상대색():
    assert opponent(BLACK) == WHITE
    assert opponent(WHITE) == BLACK


def test_판_복사는_원본을_안_건드린다():
    board = Board(9)
    board.play((4, 4), BLACK)
    copy = board.copy()
    copy.play((2, 2), WHITE)
    assert board.is_empty((2, 2))
    assert copy.get((4, 4)) == BLACK


def test_글자판_그리기():
    board = Board(9)
    board.play((4, 4), BLACK)
    글 = board.ascii()
    assert "●" in 글
    assert 글.splitlines()[0].startswith("   A B C")
