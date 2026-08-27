"""SGF 기보 읽기·쓰기 테스트."""

import pytest

from baduk.board import BLACK, WHITE, PASS, Board
from baduk.sgf import from_sgf, load_sgf, save_sgf, to_sgf


def test_왕복():
    board = Board(19, komi=6.5)
    for move in [(3, 3), (15, 15), (3, 15), (15, 3)]:
        board.play(move)
    다시 = from_sgf(to_sgf(board))
    assert 다시.moves == board.moves
    assert 다시.size == 19
    assert 다시.komi == 6.5


def test_패스도_보존된다():
    board = Board(9)
    board.play((4, 4))
    board.play(PASS)
    board.play((2, 2))
    다시 = from_sgf(to_sgf(board))
    assert 다시.moves[1][1] is PASS
    assert 다시.moves == board.moves


def test_판_크기와_덤을_읽는다():
    board = from_sgf("(;GM[1]FF[4]SZ[13]KM[7.5];B[dd];W[jj])")
    assert board.size == 13
    assert board.komi == 7.5
    assert len(board.moves) == 2


def test_접바둑_기보():
    board = Board(19)
    board.place_handicap(4)
    board.play((5, 5), WHITE)
    글 = to_sgf(board)
    assert "HA[4]" in 글
    assert "AB[" in 글
    다시 = from_sgf(글)
    assert 다시.handicap == 4
    assert sum(1 for s in 다시.stones if s == BLACK) == 4


def test_대국자_이름과_결과():
    board = Board(9)
    board.play((4, 4))
    글 = to_sgf(board, black="나", white="KataGo", result="B+2.5")
    assert "PB[나]" in 글
    assert "PW[KataGo]" in 글
    assert "RE[B+2.5]" in 글


def test_대괄호가_든_이름도_안전하다():
    board = Board(9)
    글 = to_sgf(board, black="이름] 안에", white="백")
    assert "\\]" in 글
    assert from_sgf(글).size == 9


def test_옛_방식_tt_패스():
    board = from_sgf("(;SZ[19];B[dd];W[tt];B[pp])")
    assert board.moves[1][1] is PASS


def test_변화도는_첫_갈래만_읽는다():
    board = from_sgf("(;SZ[9];B[cc](;W[dd];B[ee])(;W[ff]))")
    assert board.moves[0][1] == (2, 2)
    assert len(board.moves) >= 1


def test_형식이_아니면_거절한다():
    with pytest.raises(ValueError):
        from_sgf("이건 SGF 가 아닙니다")


def test_파일로_저장하고_읽기(tmp_path):
    board = Board(9)
    board.play((4, 4))
    board.play((2, 2))
    경로 = tmp_path / "대국.sgf"
    save_sgf(경로, board, black="나")
    다시 = load_sgf(경로)
    assert 다시.moves == board.moves


def test_판_밖_좌표는_패스로_친다():
    board = from_sgf("(;SZ[9];B[zz])")
    assert board.moves[0][1] is PASS
