# 바둑

파이썬으로 만든 바둑판입니다. **KataGo 를 붙이면 KataGo 와 둘 수 있고**,
아무것도 설치하지 않아도 내장 봇으로 바로 둘 수 있습니다.

규칙(따냄·자살수·패·계가)은 전부 직접 구현했고, 외부 라이브러리를 쓰지
않습니다. 파이썬 3.9 이상만 있으면 됩니다.

## 웹에서 바로 두기 (설치 없음)

**https://musicits.github.io/go-baduk/**

규칙과 봇이 전부 자바스크립트로 들어 있어 서버 없이 브라우저 안에서만 돕니다.
휴대폰에서도 됩니다.

단, 웹에서는 **내장 봇하고만** 둘 수 있습니다. KataGo 는 네이티브 프로그램이라
브라우저에서 돌릴 수 없기 때문입니다. KataGo 와 두시려면 아래처럼 내려받아
실행하세요.

## 바로 실행

```bash
python baduk.py            # 브라우저로 바둑판 열기
python baduk.py term       # 터미널에서 두기
python baduk.py engines    # 어떤 엔진이 잡히는지 확인
```

Windows·macOS 는 `♟_바둑 두기.bat` / `♟_바둑 두기.command` 를
더블클릭해도 됩니다.

## 기능

| | |
| --- | --- |
| 판 크기 | 9 · 13 · 19 로 |
| 규칙 | 따냄, 자살수 금지, 패(단수패), 동형반복 금지 |
| 계가 | 중국식(돌+집) · 한국식(집+사석) |
| 웹 | 설치 없이 브라우저에서 (내장 봇만) |
| 접바둑 | 2~9점 |
| 기보 | SGF 저장·불러오기 (사바키·리지·타이젬 등과 호환) |
| 분석 | KataGo 연결 시 승률·예상집·추천수 표시 |
| 그 외 | 무르기, 패스, 돌 던지기, 계가 |

## 상대 고르기

### KataGo (권장)

[KataGo](https://github.com/lightvector/KataGo) 는 공개된 오픈소스 엔진이고,
지금 개인이 쓸 수 있는 것 중 가장 강한 축입니다.

1. [릴리스 페이지](https://github.com/lightvector/KataGo/releases)에서
   내 컴퓨터에 맞는 파일을 받습니다.
   - Windows: `katago-*-opencl-windows-x64.zip` (그래픽카드 상관없이 무난)
   - macOS: `brew install katago`
   - 리눅스: 배포판 패키지 또는 릴리스의 `linux-x64` 빌드
2. [신경망 파일](https://katagotraining.org/networks/)을 하나 받습니다
   (`.bin.gz`). 최신 `b18` 계열이면 충분히 강합니다.
3. 아래 셋 중 편한 방법으로 알려줍니다.

```bash
# 방법 1 — PATH 에 katago 가 있으면 알아서 찾습니다
katago version

# 방법 2 — 환경변수로 알려주기
export KATAGO_PATH=/path/to/katago
export KATAGO_MODEL=/path/to/model.bin.gz
export KATAGO_CONFIG=/path/to/gtp.cfg     # 없으면 기본 설정을 찾아 씁니다

# 방법 3 — ~/.katago/ 폴더에 실행 파일과 신경망을 함께 두기
```

`python baduk.py engines` 로 제대로 잡혔는지 확인할 수 있습니다.

너무 강하면 약하게 만들 수 있습니다.

```bash
python baduk.py term --탐색수 20      # 탐색을 줄이면 약해지고 빨라집니다
python baduk.py term --접바둑 4        # 4점 깔고 두기
```

### 다른 GTP 엔진

GTP 를 말하는 프로그램이면 무엇이든 붙습니다 (Leela Zero, GNU Go 등).

```bash
python baduk.py term --엔진 "leelaz -g -w network.gz"
python baduk.py term --엔진 "gnugo --mode gtp"
```

### 내장 봇

아무것도 설치하지 않으면 내장 봇이 상대가 됩니다. **아주 약합니다.**
돌을 따고, 단수 맞은 돌을 살리고, 자기 눈은 안 메우는 정도만 합니다.
정석도 사활도 모릅니다. 화면과 규칙이 도는지 확인하는 용도입니다.

### 절예(Fine Art)는 붙일 수 없습니다

절예는 텐센트가 만든 **비공개 엔진**입니다. 내려받을 수 있는 배포판도,
프로그램에서 부를 수 있는 공개 API 도 없습니다. 타이젬·한큐바둑 같은
서비스 **안에서 기능으로만** 쓸 수 있고 (해당 기능은 대체로 유료 회원용),
가장 강한 판본은 중국 국가대표팀 전용입니다.

그래서 내 컴퓨터에 깔아 이 프로그램에 연결하는 방법은 없습니다.
개인이 쓸 수 있는 것 중에서는 KataGo 가 사실상 최선입니다.

만약 언젠가 GTP 를 말하는 판본을 손에 넣는다면, 그때는
`--엔진 "실행할 명령"` 으로 그대로 붙습니다. 코드를 고칠 필요는 없습니다.

## 터미널에서 두기

좌표를 그대로 칩니다.

```
흑 차례 > Q16
KataGo: D4
흑 차례 > 분석
    Q4  승률 52.3%  예상 +1.2집  방문 480
   D16  승률 51.8%  예상 +0.9집  방문 220
흑 차례 > 저장 오늘대국.sgf
```

쓸 수 있는 말: `패스` `무르기` `계가` `분석` `항복` `저장 파일명.sgf` `그만`

## 옵션

```
python baduk.py [web|term|engines] [옵션]

  --크기 {9,13,19}    판 크기 (기본 19)
  --엔진 ENGINE       auto · katago · 내장 · 또는 직접 쓴 실행 명령
  --접바둑 점          치석 수 (2~9)
  --내색 {흑,백}       내가 잡을 색 (기본 흑)
  --덤 KOMI           덤 (기본 19로 6.5, 9·13로 5.5)
  --규칙 {중국,한국}   계가 방식 (기본 중국)
  --생각시간 초        엔진이 한 수에 쓸 시간 (기본 5초)
  --탐색수 N          KataGo 탐색 수 제한 — 낮추면 약하고 빨라집니다
  --포트 PORT         웹 서버 포트 (기본 8777)
```

## 코드에서 쓰기

```python
from baduk import Board, BLACK, WHITE

board = Board(19, komi=6.5)
board.play((3, 3))                  # 흑 D16
board.play(board.from_gtp("Q4"))    # 백 Q4
print(board.ascii())
print(board.score(rules="중국"))
```

## 구성

| 파일 | 하는 일 |
| --- | --- |
| `board.py` | 규칙 — 착수·따냄·자살수·패·계가 |
| `gtp.py` | GTP 엔진 프로세스 연결 |
| `engine.py` | 상대 고르기 (KataGo 탐색 · 내장 봇) |
| `game.py` | 대국 진행 |
| `sgf.py` | 기보 저장·불러오기 |
| `server.py` | 브라우저 바둑판 (로컬 서버) |
| `cli.py` | 터미널 대국 |
| `docs/index.html` | 바둑판 화면. 로컬 서버와 GitHub Pages 가 같은 파일을 쓴다 |
| `docs/rules.js` | 규칙과 봇을 자바스크립트로 옮긴 것. 웹 전용 |

`docs/index.html` 은 열릴 때 파이썬 서버가 뒤에 있는지 확인해서, 있으면
서버(=KataGo)로 두고 없으면 브라우저 안에서 혼자 둡니다. 화면 파일이
한 벌뿐이라 양쪽이 갈라지지 않습니다.

`docs/rules.js` 와 `baduk/board.py` 는 같은 규칙을 두 번 구현한 것입니다.
동작이 어긋나면 **`board.py` 가 기준**입니다. 그쪽에만 테스트가 붙어 있습니다.

웹 서버는 `127.0.0.1` 에만 열려서 내 컴퓨터 밖에서는 접속되지 않습니다.

## 테스트

```bash
pip install pytest && python -m pytest
```

KataGo 없이도 전부 돌아갑니다. GTP 연결은 GTP 를 흉내 내는 가짜 엔진을
띄워서 확인합니다.
