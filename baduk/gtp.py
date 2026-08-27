"""GTP(Go Text Protocol) 엔진 연결.

KataGo·Leela Zero·GNU Go 처럼 GTP 를 말하는 프로그램이면 무엇이든
같은 방식으로 붙는다. 엔진을 하위 프로세스로 띄우고 명령을 주고받는다.

    engine = GtpEngine(["katago", "gtp", "-config", "...", "-model", "..."])
    engine.start()
    engine.boardsize(19)
    engine.komi(6.5)
    engine.play(BLACK, "Q16")
    print(engine.genmove(WHITE))
    engine.stop()
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import queue

from .board import BLACK, WHITE, PASS


class GtpError(RuntimeError):
    """엔진이 명령을 거절했거나 응답이 이상할 때."""


class EngineNotFound(GtpError):
    """실행 파일을 찾지 못했을 때."""


class GtpEngine:
    """GTP 엔진 프로세스 하나를 감싼다.

    :param command: 실행할 명령 (리스트).
    :param name: 화면에 보여줄 이름.
    :param cwd: 작업 폴더.
    :param timeout: 명령 하나를 기다릴 최대 초. `genmove` 는 이보다 길게 잡는다.
    """

    def __init__(self, command, name: str = None, cwd: str = None,
                 timeout: float = 30.0):
        if not command:
            raise ValueError("실행할 명령이 비었습니다")
        self.command = list(command)
        self.name = name or self.command[0]
        self.cwd = cwd
        self.timeout = timeout
        self.process = None
        self.stderr_tail = []
        self._counter = 0
        self._stderr_thread = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 수명 관리
    # ------------------------------------------------------------------
    def start(self):
        """엔진을 띄운다. 이미 떠 있으면 아무것도 하지 않는다."""
        if self.is_running():
            return self
        if shutil.which(self.command[0]) is None:
            import os
            if not os.path.isfile(self.command[0]):
                raise EngineNotFound(
                    f"실행 파일을 찾을 수 없습니다: {self.command[0]}"
                )
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise EngineNotFound(f"엔진을 띄우지 못했습니다: {exc}") from exc

        self._stderr_queue = queue.Queue()
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, daemon=True
        )
        self._stderr_thread.start()
        return self

    def is_running(self) -> bool:
        """엔진이 살아 있는지 확인한다."""
        return self.process is not None and self.process.poll() is None

    def stop(self):
        """엔진을 정리한다. 여러 번 불러도 안전하다."""
        if self.process is None:
            return
        try:
            if self.is_running():
                # 생각에 잠긴 엔진을 오래 기다리지 않는다. 안 받으면 곧 죽인다.
                self.send("quit", timeout=2.0)
        except (GtpError, OSError):
            pass
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        finally:
            for stream in (self.process.stdin, self.process.stdout,
                           self.process.stderr):
                try:
                    stream.close()
                except OSError:
                    pass
            self.process = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
        return False

    # ------------------------------------------------------------------
    # 기본 통신
    # ------------------------------------------------------------------
    def send(self, command: str, timeout: float = None) -> str:
        """GTP 명령 하나를 보내고 응답 본문을 돌려준다.

        엔진이 ``?`` 로 답하면 `GtpError` 를 던진다.
        """
        with self._lock:
            if not self.is_running():
                raise GtpError(f"{self.name} 엔진이 떠 있지 않습니다")
            self._counter += 1
            tag = self._counter
            try:
                self.process.stdin.write(f"{tag} {command}\n")
                self.process.stdin.flush()
            except OSError as exc:
                raise GtpError(f"명령을 보내지 못했습니다: {exc}") from exc
            return self._read_response(tag, timeout or self.timeout, command)

    def _read_response(self, tag: int, timeout: float, command: str) -> str:
        result = {}

        def reader():
            lines = []
            try:
                for line in self.process.stdout:
                    line = line.rstrip("\n")
                    if not lines and not line.strip():
                        continue          # 응답 앞의 빈 줄은 버린다
                    if line.strip() == "" and lines:
                        break             # 빈 줄이 응답의 끝이다
                    lines.append(line)
            except (OSError, ValueError):
                pass
            result["lines"] = lines

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            raise GtpError(
                f"{self.name} 이(가) {timeout:g}초 안에 답하지 않았습니다: {command}"
            )

        lines = result.get("lines") or []
        if not lines:
            hint = " / ".join(self.stderr_tail[-3:])
            raise GtpError(
                f"{self.name} 이(가) 응답 없이 끝났습니다: {command}"
                + (f" (엔진 메시지: {hint})" if hint else "")
            )

        head = lines[0]
        body = "\n".join([head[head.find(" ") + 1:] if " " in head else ""]
                         + lines[1:]).strip()
        if head.startswith("?"):
            raise GtpError(f"{self.name}: {body or '명령 거절'} ({command})")
        if not head.startswith("="):
            raise GtpError(f"{self.name} 응답이 이상합니다: {head}")
        return body

    def _drain_stderr(self):
        try:
            for line in self.process.stderr:
                line = line.rstrip("\n")
                if line:
                    self.stderr_tail.append(line)
                    del self.stderr_tail[:-40]
        except (OSError, ValueError):
            pass

    def supports(self, command: str) -> bool:
        """엔진이 그 명령을 아는지 확인한다."""
        try:
            return self.send("known_command " + command).lower() == "true"
        except GtpError:
            return False

    # ------------------------------------------------------------------
    # 자주 쓰는 명령
    # ------------------------------------------------------------------
    def version(self) -> str:
        """엔진 이름과 버전."""
        try:
            return f"{self.send('name')} {self.send('version')}".strip()
        except GtpError:
            return self.name

    def boardsize(self, size: int):
        """판 크기를 정한다."""
        self.send(f"boardsize {size}")
        self.send("clear_board")

    def clear_board(self):
        """판을 비운다."""
        self.send("clear_board")

    def komi(self, value: float):
        """덤을 정한다."""
        self.send(f"komi {value}")

    def handicap(self, count: int):
        """접바둑 치석을 놓게 하고 자리 목록을 돌려준다."""
        body = self.send(f"fixed_handicap {count}")
        return body.split()

    def play(self, color: int, vertex: str):
        """엔진 판에 한 수 반영한다."""
        self.send(f"play {_color(color)} {vertex}")

    def genmove(self, color: int, timeout: float = 300.0) -> str:
        """엔진에게 한 수 두게 하고 좌표를 돌려준다.

        ``pass`` 또는 ``resign`` 이 올 수 있다.
        """
        return self.send(f"genmove {_color(color)}", timeout=timeout).lower()

    def undo(self):
        """엔진 쪽에서 한 수 무른다."""
        self.send("undo")

    def set_time(self, main: int, byoyomi: int = 0, periods: int = 0):
        """시간 설정 (초). 엔진이 이 명령을 모르면 조용히 넘어간다."""
        try:
            self.send(f"time_settings {main} {byoyomi} {periods}")
        except GtpError:
            pass

    def final_score(self) -> str:
        """엔진이 센 최종 점수 (예: ``B+7.5``)."""
        return self.send("final_score", timeout=120.0)

    def dead_stones(self):
        """엔진이 죽었다고 보는 돌의 좌표 목록."""
        try:
            return self.send("final_status_list dead", timeout=120.0).split()
        except GtpError:
            return []

    # ------------------------------------------------------------------
    # KataGo 분석 (승률·예상 집)
    # ------------------------------------------------------------------
    def analyze(self, color: int, centiseconds: int = 100, max_moves: int = 5):
        """현재 국면을 분석한다. KataGo·Leela Zero 에서만 동작한다.

        :return: 후보 수 목록. 각 항목은
            ``{"수", "승률", "예상집", "방문수", "예상진행"}``.
            분석을 지원하지 않는 엔진이면 빈 리스트.
        """
        for command in ("kata-analyze", "lz-analyze"):
            if not self.supports(command):
                continue
            try:
                body = self.send(
                    f"{command} {_color(color)} interval {centiseconds}",
                    timeout=max(10.0, centiseconds / 50.0),
                )
            except GtpError:
                continue
            moves = _parse_analysis(body)
            if moves:
                return moves[:max_moves]
        return []


def _color(color) -> str:
    if color == BLACK or str(color).lower() in ("b", "black", "흑"):
        return "black"
    if color == WHITE or str(color).lower() in ("w", "white", "백"):
        return "white"
    raise ValueError(f"모르는 색입니다: {color}")


def _parse_analysis(body: str):
    """``info move Q16 visits 100 winrate 0.53 …`` 형태를 뜯는다."""
    moves = []
    for chunk in body.replace("\n", " ").split("info ")[1:]:
        tokens = chunk.split()
        entry, key = {}, None
        pv = []
        for i, token in enumerate(tokens):
            low = token.lower()
            if low == "pv":
                pv = tokens[i + 1:]
                break
            if low in ("move", "visits", "winrate", "scorelead",
                       "scoremean", "prior", "order"):
                key = low
            elif key:
                entry[key] = token
                key = None
        if "move" not in entry:
            continue
        score = entry.get("scorelead", entry.get("scoremean"))
        moves.append({
            "수": entry["move"],
            "승률": _winrate(entry.get("winrate")),
            "예상집": _num(score),
            "방문수": int(float(entry.get("visits", 0))),
            "예상진행": pv[:8],
        })
    moves.sort(key=lambda m: -m["방문수"])
    return moves


def _num(text):
    """숫자로 바꾼다. 못 바꾸면 None."""
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _winrate(text):
    """승률을 0~1 로 맞춘다. Leela Zero 는 0~10000 으로 주기 때문이다."""
    value = _num(text)
    if value is None:
        return None
    if value > 1.5:
        return min(1.0, value / 10000.0)
    return value
