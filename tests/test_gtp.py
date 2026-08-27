"""GTP 엔진 연결 테스트.

진짜 KataGo 없이도 확인할 수 있게, GTP 를 흉내 내는 작은 파이썬
프로그램을 하위 프로세스로 띄워서 주고받는다.
"""

import sys
import textwrap

import pytest

from baduk.board import BLACK, WHITE
from baduk.gtp import GtpEngine, GtpError, EngineNotFound, _parse_analysis, _winrate

FAKE = textwrap.dedent('''
    import sys
    수순 = []
    for 줄 in sys.stdin:
        줄 = 줄.strip()
        if not 줄:
            continue
        조각 = 줄.split()
        번호 = ""
        if 조각[0].isdigit():
            번호, 조각 = 조각[0], 조각[1:]
        명령 = 조각[0] if 조각 else ""
        답 = ""
        if 명령 == "quit":
            print(f"={번호} \\n"); sys.stdout.flush(); break
        elif 명령 == "name": 답 = "가짜엔진"
        elif 명령 == "version": 답 = "1.0"
        elif 명령 == "known_command":
            답 = "true" if 조각[1] in ("kata-analyze", "genmove") else "false"
        elif 명령 == "genmove": 답 = "Q16"
        elif 명령 == "final_score": 답 = "B+7.5"
        elif 명령 == "final_status_list": 답 = "A1 B2"
        elif 명령 == "kata-analyze":
            답 = "info move Q16 visits 100 winrate 0.55 scoreLead 2.5 pv Q16 D4"
        elif 명령 == "부러진명령":
            print(f"?{번호} 그런 명령 없음\\n"); sys.stdout.flush(); continue
        elif 명령 == "느린명령":
            import time; time.sleep(30)
        print(f"={번호} {답}\\n"); sys.stdout.flush()
''')


@pytest.fixture
def 엔진(tmp_path):
    경로 = tmp_path / "fake_gtp.py"
    경로.write_text(FAKE, encoding="utf-8")
    엔진 = GtpEngine([sys.executable, str(경로)], name="가짜", timeout=10)
    엔진.start()
    yield 엔진
    엔진.stop()


def test_이름과_버전(엔진):
    assert 엔진.version() == "가짜엔진 1.0"


def test_판_설정과_착수(엔진):
    엔진.boardsize(19)
    엔진.komi(6.5)
    엔진.play(BLACK, "Q16")
    assert 엔진.genmove(WHITE) == "q16"


def test_아는_명령_확인(엔진):
    assert 엔진.supports("genmove") is True
    assert 엔진.supports("없는명령") is False


def test_엔진이_거절하면_예외(엔진):
    with pytest.raises(GtpError, match="그런 명령 없음"):
        엔진.send("부러진명령")


def test_응답이_늦으면_예외(엔진):
    with pytest.raises(GtpError, match="답하지 않"):
        엔진.send("느린명령", timeout=0.5)


def test_분석_결과를_뜯는다(엔진):
    후보 = 엔진.analyze(BLACK, centiseconds=10)
    assert 후보[0]["수"] == "Q16"
    assert 후보[0]["승률"] == 0.55
    assert 후보[0]["예상집"] == 2.5
    assert 후보[0]["예상진행"][:2] == ["Q16", "D4"]


def test_죽은_돌_목록(엔진):
    assert 엔진.dead_stones() == ["A1", "B2"]


def test_최종_점수(엔진):
    assert 엔진.final_score() == "B+7.5"


def test_정리는_여러_번_불러도_안전하다(엔진):
    엔진.stop()
    엔진.stop()
    assert 엔진.is_running() is False


def test_끝난_엔진에_보내면_예외(엔진):
    엔진.stop()
    with pytest.raises(GtpError, match="떠 있지 않"):
        엔진.send("name")


def test_없는_실행파일():
    with pytest.raises(EngineNotFound):
        GtpEngine(["이런_프로그램은_없다_12345"]).start()


def test_빈_명령은_거절한다():
    with pytest.raises(ValueError):
        GtpEngine([])


def test_with_문으로_쓸_수_있다(tmp_path):
    경로 = tmp_path / "fake_gtp.py"
    경로.write_text(FAKE, encoding="utf-8")
    with GtpEngine([sys.executable, str(경로)], timeout=10) as 엔진:
        assert 엔진.is_running()


def test_릴라제로_승률_눈금():
    assert _winrate("5500") == 0.55
    assert _winrate("0.55") == 0.55
    assert _winrate(None) is None


def test_분석_문자열이_비면_빈_목록():
    assert _parse_analysis("") == []
