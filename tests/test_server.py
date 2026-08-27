"""웹 서버 테스트. 실제로 서버를 띄우고 HTTP 로 두어 본다."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from baduk import server as 서버


@pytest.fixture
def 주소():
    """빈 포트에 서버를 띄우고 주소를 준다."""
    서버.SESSION.close()
    실체 = ThreadingHTTPServer(("127.0.0.1", 0), 서버.Handler)
    실 = threading.Thread(target=실체.serve_forever, daemon=True)
    실.start()
    yield f"http://127.0.0.1:{실체.server_address[1]}"
    실체.shutdown()
    실체.server_close()
    서버.SESSION.close()


def 보내기(주소, 길, 몸통=None):
    # 몸통이 없어도 POST 로 보내야 한다 (data=None 이면 GET 이 된다).
    자료 = json.dumps(몸통 or {}).encode("utf-8")
    요청 = urllib.request.Request(
        주소 + 길, data=자료,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(요청, timeout=20) as 응답:
        return json.loads(응답.read().decode("utf-8"))


def test_첫_화면이_뜬다(주소):
    with urllib.request.urlopen(주소 + "/", timeout=10) as 응답:
        글 = 응답.read().decode("utf-8")
    assert 응답.status == 200
    assert "<canvas" in 글
    assert "바둑" in 글


def test_새_대국을_연다(주소):
    상태 = 보내기(주소, "/api/new",
               {"크기": 9, "엔진": "내장", "덤": 5.5, "규칙": "중국"})
    assert 상태["크기"] == 9
    assert 상태["수순"] == 0
    assert len(상태["돌"]) == 81


def test_두면_엔진이_받는다(주소):
    보내기(주소, "/api/new", {"크기": 9, "엔진": "내장"})
    상태 = 보내기(주소, "/api/play", {"행": 4, "열": 4})
    assert 상태["수순"] == 2                    # 내 수 + 엔진 응수
    assert 상태["돌"][4 * 9 + 4] == 1
    assert 상태["차례"] == 1


def test_같은_자리에_또_두면_400(주소):
    보내기(주소, "/api/new", {"크기": 9, "엔진": "내장"})
    보내기(주소, "/api/play", {"행": 4, "열": 4})
    with pytest.raises(urllib.error.HTTPError) as 사고:
        보내기(주소, "/api/play", {"행": 4, "열": 4})
    assert 사고.value.code == 400
    assert "이미 돌이" in json.loads(사고.value.read())["오류"]


def test_무르기(주소):
    보내기(주소, "/api/new", {"크기": 9, "엔진": "내장"})
    보내기(주소, "/api/play", {"행": 4, "열": 4})
    상태 = 보내기(주소, "/api/undo", {"수": 2})
    assert 상태["수순"] == 0
    assert 상태["돌"][4 * 9 + 4] == 0


def test_패스와_돌_던지기(주소):
    보내기(주소, "/api/new", {"크기": 9, "엔진": "내장"})
    보내기(주소, "/api/pass")
    상태 = 보내기(주소, "/api/resign")
    assert 상태["끝남"] is True
    assert "불계" in 상태["결과"]


def test_계가(주소):
    보내기(주소, "/api/new", {"크기": 9, "엔진": "내장", "규칙": "일본"})
    상태 = 보내기(주소, "/api/score")
    assert 상태["집계산"]["규칙"] == "일본"
    assert "결과" in 상태["집계산"]


def test_기보를_내려받는다(주소):
    보내기(주소, "/api/new", {"크기": 9, "엔진": "내장"})
    보내기(주소, "/api/play", {"행": 4, "열": 4})
    with urllib.request.urlopen(주소 + "/api/sgf", timeout=10) as 응답:
        글 = 응답.read().decode("utf-8")
    assert 글.startswith("(;")
    assert "SZ[9]" in 글
    assert ";B[ee]" in 글


def test_기보를_불러온다(주소):
    보내기(주소, "/api/new", {"크기": 9, "엔진": "내장"})
    상태 = 보내기(주소, "/api/load",
               {"sgf": "(;GM[1]FF[4]SZ[9]KM[5.5];B[ee];W[cc])"})
    assert 상태["수순"] == 2
    assert 상태["돌"][4 * 9 + 4] == 1


def test_망가진_기보는_거절한다(주소):
    """입력이 잘못된 것이므로 서버 오류(500)가 아니라 400 이어야 한다."""
    with pytest.raises(urllib.error.HTTPError) as 사고:
        보내기(주소, "/api/load", {"sgf": "이건 기보가 아닙니다"})
    assert 사고.value.code == 400
    assert "SGF" in json.loads(사고.value.read())["오류"]


def test_엔진_현황을_알려준다(주소):
    with urllib.request.urlopen(주소 + "/api/engines", timeout=10) as 응답:
        현황 = json.loads(응답.read().decode("utf-8"))
    assert 현황["내장 봇"]["설치됨"] is True
    assert "절예" in 현황


def test_사람이_백이면_엔진이_먼저_둔다(주소):
    상태 = 보내기(주소, "/api/new",
               {"크기": 9, "엔진": "내장", "사람": "백"})
    assert 상태["수순"] == 1
    assert 상태["차례"] == 2


def test_없는_주소는_404(주소):
    with pytest.raises(urllib.error.HTTPError) as 사고:
        urllib.request.urlopen(주소 + "/nowhere", timeout=10)
    assert 사고.value.code == 404


def test_상태를_그냥_물어봐도_대국이_생긴다(주소):
    with urllib.request.urlopen(주소 + "/api/state", timeout=20) as 응답:
        상태 = json.loads(응답.read().decode("utf-8"))
    assert 상태["크기"] == 19
    assert 상태["엔진현황"]["내장 봇"]["설치됨"] is True


def test_한글_파일명으로_받아도_안_끊긴다(주소):
    """HTTP 헤더에 한글을 그대로 넣으면 연결이 끊긴다. 인코딩해서 보내야 한다."""
    보내기(주소, "/api/new", {"크기": 9, "엔진": "내장"})
    with urllib.request.urlopen(주소 + "/api/sgf?name=%EB%8C%80%EA%B5%AD", timeout=10) as 응답:
        머리 = 응답.headers["Content-Disposition"]
        글 = 응답.read().decode("utf-8")
    assert "filename*=UTF-8''" in 머리
    assert 글.startswith("(;")
