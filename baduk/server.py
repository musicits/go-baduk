"""로컬 웹 서버.

브라우저로 바둑판을 띄워서 두는 화면을 제공한다. 파이썬 기본 모듈만 쓴다.
내 컴퓨터에서만 접속되게 127.0.0.1 에 연다.

    python baduk.py web

`/api/*` 로 JSON 을 주고받고, 판 그리기는 브라우저가 한다.
"""

from __future__ import annotations

import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs

from .board import BLACK, WHITE, PASS, IllegalMove
from .engine import engine_status
from .game import Game, new_game
from .sgf import from_sgf

# 화면 파일은 docs/ 한 곳에만 둔다. GitHub Pages 가 그 폴더를 그대로 올리므로
# 로컬 서버와 웹 페이지가 같은 파일을 쓴다.
WEB_DIR = Path(__file__).resolve().parent.parent / "docs"


class GameSession:
    """서버가 들고 있는 대국 하나. 요청이 겹쳐도 안전하게 잠금을 건다."""

    def __init__(self):
        self.game = None
        self.lock = threading.Lock()
        self.options = {}
        self.last_error = None

    def start(self, **options):
        """새 대국을 시작한다.

        엔진이 말썽이면 내장 봇으로 물러난다. 화면까지 죽으면 안 된다.
        """
        self.close()
        self.options = options
        self.last_error = None
        try:
            self.game = new_game(**options)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            print(f"\n[엔진 오류] {exc}\n", file=sys.stderr)
            물러난 = dict(options)
            물러난["engine"] = "내장"
            self.game = new_game(**물러난)
        return self.game

    def ensure(self) -> Game:
        """대국이 없으면 기본값으로 하나 만든다."""
        if self.game is None:
            self.start()
        return self.game

    def close(self):
        if self.game is not None:
            try:
                self.game.close()
            except Exception:
                pass
            self.game = None


SESSION = GameSession()


class Handler(BaseHTTPRequestHandler):
    """정적 파일과 JSON API 를 함께 처리한다."""

    server_version = "baduk-py"

    def log_message(self, fmt, *args):
        pass                                   # 콘솔을 조용하게 둔다

    # ------------------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        if path in ("/", "/index.html"):
            return self._send_file(WEB_DIR / "index.html", "text/html")
        if path == "/api/state":
            return self._json(self._state())
        if path == "/api/engines":
            return self._json(engine_status())
        if path == "/api/sgf":
            game = SESSION.ensure()
            body = game.sgf().encode("utf-8")
            name = _safe_name(query.get("name", ["대국"])[0])
            self.send_response(200)
            self.send_header("Content-Type", "application/x-go-sgf; charset=utf-8")
            # HTTP 헤더는 한글을 그대로 못 담는다. ASCII 이름을 먼저 주고
            # 한글 이름은 RFC 5987 방식으로 따로 붙인다.
            self.send_header(
                "Content-Disposition",
                'attachment; filename="baduk.sgf"; '
                f"filename*=UTF-8''{quote(name)}.sgf"
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)

        candidate = (WEB_DIR / path.lstrip("/")).resolve()
        if candidate.is_file() and WEB_DIR.resolve() in candidate.parents:
            kind = "text/css" if candidate.suffix == ".css" else "text/javascript"
            return self._send_file(candidate, kind)
        return self._error(404, "그런 주소가 없습니다")

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
        except ValueError as exc:
            return self._error(400, str(exc))

        handlers = {
            "/api/new": self._new_game,
            "/api/play": self._play,
            "/api/pass": self._pass,
            "/api/resign": self._resign,
            "/api/undo": self._undo,
            "/api/analyze": self._analyze,
            "/api/score": self._score,
            "/api/load": self._load,
            "/api/botmove": self._botmove,
        }
        handler = handlers.get(path)
        if handler is None:
            return self._error(404, "그런 주소가 없습니다")
        try:
            with SESSION.lock:
                return self._json(handler(payload))
        except IllegalMove as exc:
            return self._error(400, str(exc))
        except ValueError as exc:
            return self._error(400, str(exc))
        except Exception as exc:                       # 엔진 사고까지 화면에 알린다
            return self._error(500, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------
    # API 구현
    # ------------------------------------------------------------------
    def _new_game(self, payload):
        human = payload.get("사람", "흑")
        SESSION.start(
            size=int(payload.get("크기", 19)),
            engine=payload.get("엔진", "auto"),
            handicap=int(payload.get("접바둑", 0)),
            human=BLACK if human in ("흑", BLACK, "black") else WHITE,
            komi=payload.get("덤"),
            think_time=float(payload.get("생각시간", 5)),
            visits=payload.get("탐색수"),
            rules=payload.get("규칙", "중국"),
        )
        game = SESSION.game
        # 사람이 백이면 엔진이 먼저 둔다.
        if not game.human_turn() and not game.finished:
            game.play_bot()
        return self._state()

    def _play(self, payload):
        game = SESSION.ensure()
        move = (int(payload["행"]), int(payload["열"]))
        game.play_human(move)
        if payload.get("엔진응수", True) and not game.finished:
            game.play_bot()
        return self._state()

    def _pass(self, payload):
        game = SESSION.ensure()
        game.pass_turn()
        if not game.finished:
            game.play_bot()
        return self._state()

    def _botmove(self, payload):
        game = SESSION.ensure()
        game.play_bot()
        return self._state()

    def _resign(self, payload):
        game = SESSION.ensure()
        game.resign(game.human if game.human is not None else game.to_play)
        return self._state()

    def _undo(self, payload):
        game = SESSION.ensure()
        game.undo(int(payload.get("수", 2)))
        return self._state()

    def _analyze(self, payload):
        game = SESSION.ensure()
        game.analyze()
        return self._state()

    def _score(self, payload):
        game = SESSION.ensure()
        state = self._state()
        state["집계산"] = game.score()
        return state

    def _load(self, payload):
        text = payload.get("sgf", "")
        board = from_sgf(text)
        options = dict(SESSION.options)
        options.update(size=board.size, komi=board.komi)
        SESSION.start(**options)
        game = SESSION.game
        game.board = board
        game.bot.setup(board)
        return self._state()

    def _state(self):
        game = SESSION.ensure()
        state = game.state()
        state["엔진현황"] = engine_status()
        state["엔진오류"] = SESSION.last_error
        return state

    # ------------------------------------------------------------------
    # 보내기 도구
    # ------------------------------------------------------------------
    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"요청을 읽지 못했습니다: {exc}") from None

    def _json(self, data, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, kind: str):
        try:
            body = path.read_bytes()
        except OSError:
            return self._error(404, f"파일이 없습니다: {path.name}")
        self.send_response(200)
        self.send_header("Content-Type", f"{kind}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str):
        self._json({"오류": message}, status)


def _safe_name(name: str) -> str:
    """파일 이름에서 헤더를 망가뜨릴 글자를 걷어낸다."""
    cleaned = "".join(
        ch for ch in str(name)[:60]
        if ch not in '\r\n"\\/' and ch.isprintable()
    ).strip()
    return cleaned or "대국"


def serve(port: int = 8777, open_browser: bool = True, host: str = "127.0.0.1"):
    """서버를 띄운다. Ctrl+C 로 멈춘다."""
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"바둑판을 열었습니다 → {url}")
    print("멈추려면 이 창에서 Ctrl+C 를 누르세요.")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 닫습니다.")
    finally:
        SESSION.close()
        server.server_close()
    return 0
