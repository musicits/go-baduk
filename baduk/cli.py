"""터미널에서 바둑 두기.

    python baduk.py                 # 브라우저로 바둑판 열기
    python baduk.py term            # 터미널에서 두기
    python baduk.py term --크기 9 --접바둑 4
    python baduk.py engines         # 엔진 설치 상태 보기

터미널 대국에서는 ``Q16`` 처럼 좌표를 치면 그 자리에 둔다.
``패스`` ``무르기`` ``계가`` ``저장 파일명.sgf`` ``분석`` ``항복`` ``그만`` 도 된다.
"""

from __future__ import annotations

import argparse
import json
import sys

from .board import BLACK, WHITE, PASS, IllegalMove, color_name
from .engine import engine_status
from .game import new_game
from .sgf import save_sgf

_HELP = """
둘 자리: Q16 처럼 입력   |   패스 · 무르기 · 계가 · 분석 · 항복 · 그만
기보 저장: 저장 대국.sgf
""".strip()


def build_parser() -> argparse.ArgumentParser:
    """명령줄 옵션을 정의한다."""
    parser = argparse.ArgumentParser(
        prog="baduk",
        description="바둑 두기 (KataGo 를 붙이면 KataGo 가 상대가 됩니다)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "모드", nargs="?", default="web",
        choices=["web", "term", "engines"],
        help="web=브라우저(기본), term=터미널, engines=엔진 상태",
    )
    parser.add_argument("--크기", type=int, default=19, choices=[9, 13, 19],
                        help="판 크기 (기본 19)")
    parser.add_argument("--엔진", default="auto",
                        help="auto · katago · 내장 · 또는 직접 쓴 실행 명령")
    parser.add_argument("--접바둑", type=int, default=0, metavar="점",
                        help="치석 수 (2~9)")
    parser.add_argument("--내색", default="흑", choices=["흑", "백"],
                        help="내가 잡을 색 (기본 흑)")
    parser.add_argument("--덤", type=float, default=None, help="덤 (기본 6.5)")
    parser.add_argument("--규칙", default="중국",
                        choices=["중국", "한국"],
                        help="계가 방식 (기본 중국)")
    parser.add_argument("--생각시간", type=float, default=5.0, metavar="초",
                        help="엔진이 한 수에 쓸 시간 (기본 5초)")
    parser.add_argument("--탐색수", type=int, default=None, metavar="N",
                        help="KataGo 탐색 수 제한. 낮추면 약해지고 빨라집니다")
    parser.add_argument("--포트", type=int, default=8777, help="웹 서버 포트")
    parser.add_argument("--브라우저-안열기", action="store_true",
                        dest="브라우저_안열기", help="브라우저를 자동으로 열지 않음")
    return parser


def main(argv=None) -> int:
    """진입점."""
    args = build_parser().parse_args(argv)

    if args.모드 == "engines":
        print(json.dumps(engine_status(), ensure_ascii=False, indent=2))
        return 0

    if args.모드 == "web":
        from .server import serve
        return serve(port=args.포트, open_browser=not args.브라우저_안열기)

    return play_terminal(args)


def play_terminal(args) -> int:
    """터미널에서 한 판 둔다."""
    try:
        game = new_game(
            size=args.크기, engine=args.엔진, handicap=args.접바둑,
            human=BLACK if args.내색 == "흑" else WHITE, komi=args.덤,
            think_time=args.생각시간, visits=args.탐색수, rules=args.규칙,
        )
    except Exception as exc:
        print(f"대국을 시작하지 못했습니다: {exc}", file=sys.stderr)
        return 1

    print(f"\n상대: {game.bot.name} ({game.bot.strength})")
    print(f"판 {args.크기}로 · 덤 {game.board.komi} · {args.규칙}식 계가")
    if args.접바둑 >= 2:
        print(f"{args.접바둑}점 접바둑")
    print(_HELP)

    try:
        while not game.finished:
            if not game.human_turn():
                move = game.play_bot()
                label = "돌을 던졌습니다" if move == "resign" else (
                    "패스" if move is PASS else game.board.to_gtp(move))
                print(f"\n{game.bot.name}: {label}")
                _show(game)
                continue

            _show(game)
            try:
                raw = input(f"{color_name(game.to_play)} 차례 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n대국을 중단합니다.")
                return 0
            if not _command(game, raw):
                return 0
    finally:
        game.close()

    _show(game)
    print(f"\n대국 종료 — {game.result}")
    if not game.resigned_by:
        점수 = game.score()
        print(f"흑 {점수['흑']} · 백 {점수['백']} ({점수['규칙']}식, 덤 {점수['덤']})")
    return 0


def _command(game, raw: str) -> bool:
    """입력 한 줄을 처리한다. False 를 돌려주면 대국을 끝낸다."""
    if not raw:
        return True
    word = raw.split()[0]

    if word in ("그만", "quit", "exit"):
        print("대국을 중단합니다.")
        return False
    if word in ("도움", "help", "?"):
        print(_HELP)
        return True
    if word in ("패스", "pass"):
        game.pass_turn()
        if not game.finished:
            move = game.play_bot()
            print(f"{game.bot.name}: "
                  f"{'패스' if move is PASS else game.board.to_gtp(move)}")
        return True
    if word in ("무르기", "undo"):
        done = game.undo(2)
        print(f"{done}수 물렀습니다." if done else "무를 수가 없습니다.")
        return True
    if word in ("항복", "resign"):
        print(game.resign())
        return False
    if word in ("계가", "score"):
        점수 = game.score()
        print(f"{점수['규칙']}식 — 흑 {점수['흑']} · 백 {점수['백']} → {점수['결과']}")
        return True
    if word in ("분석", "analyze"):
        후보 = game.analyze()
        if not 후보:
            print("이 엔진은 분석을 지원하지 않습니다 (KataGo 를 붙이세요).")
        for 수 in 후보:
            승 = "–" if 수["승률"] is None else f"{수['승률'] * 100:.1f}%"
            집 = "–" if 수["예상집"] is None else f"{수['예상집']:+.1f}"
            print(f"  {수['수']:>4}  승률 {승}  예상 {집}집  방문 {수['방문수']}")
        return True
    if word in ("저장", "save"):
        parts = raw.split(maxsplit=1)
        path = parts[1].strip() if len(parts) > 1 else "대국.sgf"
        save_sgf(path, game.board, result=game.result)
        print(f"저장했습니다: {path}")
        return True

    try:
        move = game.board.from_gtp(raw)
    except ValueError as exc:
        print(f"{exc}  ({_HELP.splitlines()[0]})")
        return True

    try:
        game.play_human(move)
    except IllegalMove as exc:
        print(f"둘 수 없습니다: {exc}")
        return True

    if not game.finished:
        move = game.play_bot()
        label = "돌을 던졌습니다" if move == "resign" else (
            "패스" if move is PASS else game.board.to_gtp(move))
        print(f"{game.bot.name}: {label}")
    return True


def _show(game):
    board = game.board
    marks = {}
    for _, move in reversed(board.moves):
        if move is not PASS:
            marks[move] = "◉" if board.get(move) == BLACK else "◎"
            break
    print()
    print(board.ascii(marks))
    print(f"따낸 돌 — 흑 {board.captures[BLACK]} · 백 {board.captures[WHITE]}"
          f"   |   {len(board.moves)}수")
