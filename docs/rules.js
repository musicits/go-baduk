/* 바둑 규칙 엔진 (브라우저용).
 *
 * baduk/board.py 와 같은 규칙을 자바스크립트로 옮긴 것이다.
 * 서버 없이 GitHub Pages 같은 정적 호스팅에서도 그대로 돌아간다.
 * 파이썬 쪽과 동작이 어긋나면 board.py 가 기준이다.
 */
"use strict";

// 안쪽 이름이 페이지의 다른 스크립트와 부딪히지 않게 감싼다.
// 밖으로 나가는 것은 맨 아래 window.바둑 하나뿐이다.
(function () {

  const 빈칸 = 0, 흑 = 1, 백 = 2;
  const 글자표 = "ABCDEFGHJKLMNOPQRSTUVWXYZ";   // I 는 1 과 헷갈려서 뺀다

  function 상대(색) { return 색 === 흑 ? 백 : 흑; }
  function 색이름(색) { return 색 === 흑 ? "흑" : 색 === 백 ? "백" : "빈칸"; }

  class 위법수 extends Error {}

  class 바둑판 {
    constructor(크기 = 19, 덤 = 6.5, 동형반복금지 = true) {
      if (크기 < 2 || 크기 > 25) throw new Error("판 크기는 2~25 사이여야 합니다");
      this.크기 = 크기;
      this.덤 = 덤;
      this.동형반복금지 = 동형반복금지;
      this.돌 = new Int8Array(크기 * 크기);
      this.따낸돌 = { [흑]: 0, [백]: 0 };
      this.차례 = 흑;
      this.패 = null;              // 되따내기가 막힌 자리 (index)
      this.수순 = [];              // [[색, 수], ...]  수는 [행,열] 또는 null(패스)
      this.접바둑 = 0;
      this._이웃 = 이웃표(크기);
      this._되돌리기 = [];
      this._본판 = new Set([this._열쇠()]);
    }

    // -- 좌표 -----------------------------------------------------------
    번호(수) {
      const [행, 열] = 수;
      if (행 < 0 || 열 < 0 || 행 >= this.크기 || 열 >= this.크기)
        throw new 위법수(`판 밖입니다: ${수}`);
      return 행 * this.크기 + 열;
    }
    자리(번호) { return [Math.floor(번호 / this.크기), 번호 % this.크기]; }

    좌표(수) {
      if (수 === null) return "pass";
      return 글자표[수[1]] + (this.크기 - 수[0]);
    }
    좌표풀기(글) {
      글 = String(글).trim().toUpperCase();
      if (글 === "PASS" ||글 === "") return null;
      const 열 = 글자표.indexOf(글[0]);
      const 번 = parseInt(글.slice(1), 10);
      if (열 < 0 || isNaN(번)) throw new Error(`좌표를 알 수 없습니다: ${글}`);
      const 행 = this.크기 - 번;
      if (행 < 0 || 행 >= this.크기 || 열 >= this.크기)
        throw new Error(`판 밖입니다: ${글}`);
      return [행, 열];
    }

    // -- 판 읽기 --------------------------------------------------------
    읽기(수) { return this.돌[this.번호(수)]; }
    비었나(수) { return this.읽기(수) === 빈칸; }

    단위(번호) {
      const 색 = this.돌[번호];
      const 쌓기 = [번호], 모임 = new Set([번호]), 활로 = new Set();
      while (쌓기.length) {
        const i = 쌓기.pop();
        for (const j of this._이웃[i]) {
          const 것 = this.돌[j];
          if (것 === 빈칸) 활로.add(j);
          else if (것 === 색 && !모임.has(j)) { 모임.add(j); 쌓기.push(j); }
        }
      }
      return [모임, 활로];
    }

    활로수(수) { return this.단위(this.번호(수))[1].size; }

    합법인가(수, 색) {
      if (수 === null) return true;
      try { this._확인(수, 색 === undefined ? this.차례 : 색); }
      catch (e) { if (e instanceof 위법수) return false; throw e; }
      return true;
    }

    위법사유(수, 색) {
      if (수 === null) return null;
      try { this._확인(수, 색 === undefined ? this.차례 : 색); }
      catch (e) { if (e instanceof 위법수) return e.message; throw e; }
      return null;
    }

    둘수있는곳(색) {
      색 = 색 === undefined ? this.차례 : 색;
      const 결과 = [];
      for (let i = 0; i < this.돌.length; i++) {
        if (this.돌[i] !== 빈칸) continue;
        const 수 = this.자리(i);
        if (this.합법인가(수, 색)) 결과.push(수);
      }
      return 결과;
    }

    // -- 착수 -----------------------------------------------------------
    두기(수, 색) {
      색 = 색 === undefined ? this.차례 : 색;
      const 사진 = [
        new Int8Array(this.돌), { ...this.따낸돌 }, this.차례,
        this.패, this.수순.length, new Set(this._본판),
      ];

      if (수 === null) {
        this._되돌리기.push(사진);
        this.패 = null;
        this.수순.push([색, null]);
        this.차례 = 상대(색);
        return 0;
      }

      const 잡힌돌 = this._확인(수, 색);
      const 번호 = this.번호(수);

      this._되돌리기.push(사진);
      this.돌[번호] = 색;
      for (const 죽은 of 잡힌돌) this.돌[죽은] = 빈칸;
      this.따낸돌[색] += 잡힌돌.size;

      // 한 점만 따냈는데 내 돌도 한 점 단수면 그 자리가 패다.
      this.패 = null;
      if (잡힌돌.size === 1) {
        const [내것, 활로] = this.단위(번호);
        if (내것.size === 1 && 활로.size === 1) this.패 = [...잡힌돌][0];
      }

      this.수순.push([색, 수]);
      this.차례 = 상대(색);
      this._본판.add(this._열쇠());
      return 잡힌돌.size;
    }

    되돌리기() {
      if (!this._되돌리기.length) return false;
      const [돌, 따낸돌, 차례, 패, 수, 본판] = this._되돌리기.pop();
      this.돌 = 돌;
      this.따낸돌 = 따낸돌;
      this.차례 = 차례;
      this.패 = 패;
      this.수순.length = 수;
      this._본판 = 본판;
      return true;
    }

    치석놓기(수) {
      const 자리들 = 치석자리(this.크기, 수);
      for (const 점 of 자리들) this.돌[this.번호(점)] = 흑;
      if (자리들.length) {
        this.접바둑 = 자리들.length;
        this.차례 = 백;                       // 치석을 놓으면 백이 먼저
        this._되돌리기.length = 0;
        this._본판 = new Set([this._열쇠()]);
      }
      return 자리들;
    }

    끝났나() {
      const n = this.수순.length;
      return n >= 2 && this.수순[n - 1][1] === null && this.수순[n - 2][1] === null;
    }

    // -- 집 계산 --------------------------------------------------------
    집(죽은돌 = []) {
      const 돌 = new Int8Array(this.돌);
      const 사석 = { [흑]: 0, [백]: 0 };
      for (const 점 of 죽은돌) {
        const i = this.번호(점);
        if (돌[i] !== 빈칸) { 사석[돌[i]] += 1; 돌[i] = 빈칸; }
      }

      const 셈 = { [흑]: 0, [백]: 0, 중립: 0 };
      const 다녀감 = new Uint8Array(돌.length);
      for (let 시작 = 0; 시작 < 돌.length; 시작++) {
        if (돌[시작] !== 빈칸 || 다녀감[시작]) continue;
        let 넓이 = 0;
        const 경계 = new Set(), 쌓기 = [시작];
        다녀감[시작] = 1;
        while (쌓기.length) {
          const i = 쌓기.pop();
          넓이++;
          for (const j of this._이웃[i]) {
            if (돌[j] === 빈칸) {
              if (!다녀감[j]) { 다녀감[j] = 1; 쌓기.push(j); }
            } else 경계.add(돌[j]);
          }
        }
        if (경계.size === 1) 셈[[...경계][0]] += 넓이;
        else 셈.중립 += 넓이;
      }
      셈.사석 = 사석;
      return 셈;
    }

    계가(죽은돌 = [], 규칙 = "중국") {
      const 셈 = this.집(죽은돌);
      const 죽은번호 = new Set(죽은돌.map(p => this.번호(p)));
      let 흑점, 백점;

      if (규칙 === "중국") {
        const 살아있음 = { [흑]: 0, [백]: 0 };
        for (let i = 0; i < this.돌.length; i++)
          if (this.돌[i] !== 빈칸 && !죽은번호.has(i)) 살아있음[this.돌[i]]++;
        흑점 = 셈[흑] + 살아있음[흑];
        백점 = 셈[백] + 살아있음[백] + this.덤;
      } else if (규칙 === "한국") {
        흑점 = 셈[흑] + this.따낸돌[흑] + 셈.사석[백];
        백점 = 셈[백] + this.따낸돌[백] + 셈.사석[흑] + this.덤;
      } else throw new Error(`모르는 규칙입니다: ${규칙} (중국·한국)`);

      const 차이 = 흑점 - 백점;
      const 결과 = 차이 > 0 ? `흑 ${깔끔(차이)}집 승`
                : 차이 < 0 ? `백 ${깔끔(-차이)}집 승` : "무승부";
      return { 규칙, 흑: 흑점, 백: 백점, 차이, 결과, 덤: this.덤, 공배: 셈.중립 };
    }

    // -- 내부 -----------------------------------------------------------
    _확인(수, 색) {
      const 번호 = this.번호(수);
      if (this.돌[번호] !== 빈칸) throw new 위법수("이미 돌이 있습니다");
      if (번호 === this.패) throw new 위법수("패입니다 — 다른 곳을 먼저 두세요");

      const 적 = 상대(색);
      const 잡힌돌 = new Set();
      for (const j of this._이웃[번호]) {
        if (this.돌[j] !== 적 || 잡힌돌.has(j)) continue;
        const [모임, 활로] = this.단위(j);
        if (활로.size === 1 && 활로.has(번호))
          for (const s of 모임) 잡힌돌.add(s);
      }

      if (!잡힌돌.size) {
        // 따낼 게 없으면 내 돌이 살아남는지 본다.
        this.돌[번호] = 색;
        const 활로 = this.단위(번호)[1];
        this.돌[번호] = 빈칸;
        if (!활로.size) throw new 위법수("자살수입니다");
      }

      if (this.동형반복금지) {
        this.돌[번호] = 색;
        for (const 죽은 of 잡힌돌) this.돌[죽은] = 빈칸;
        const 반복 = this._본판.has(상대(색) + "|" + this.돌.join(""));
        this.돌[번호] = 빈칸;
        for (const 죽은 of 잡힌돌) this.돌[죽은] = 적;
        if (반복) throw new 위법수("같은 판이 반복됩니다 (동형반복 금지)");
      }
      return 잡힌돌;
    }

    _열쇠() { return this.차례 + "|" + this.돌.join(""); }
  }

  function 이웃표(크기) {
    const 표 = [];
    for (let i = 0; i < 크기 * 크기; i++) {
      const 행 = Math.floor(i / 크기), 열 = i % 크기, 가까이 = [];
      if (행 > 0) 가까이.push(i - 크기);
      if (행 < 크기 - 1) 가까이.push(i + 크기);
      if (열 > 0) 가까이.push(i - 1);
      if (열 < 크기 - 1) 가까이.push(i + 1);
      표.push(가까이);
    }
    return 표;
  }

  function 깔끔(값) { return Number.isInteger(값) ? String(값) : String(값); }

  function 화점자리(크기) {
    if (크기 < 7) return [];
    const 끝 = 크기 >= 13 ? 3 : 2, 가운데 = (크기 - 1) / 2, 먼 = 크기 - 1 - 끝;
    const 점 = [[끝, 끝], [끝, 먼], [먼, 끝], [먼, 먼]];
    if (크기 % 2 === 1 && 크기 >= 9) {
      점.push([가운데, 가운데]);
      if (크기 >= 13) 점.push([끝, 가운데], [먼, 가운데], [가운데, 끝], [가운데, 먼]);
    }
    return 점;
  }

  function 치석자리(크기, 수) {
    if (수 < 2) return [];
    if (크기 < 9 || 크기 % 2 === 0)
      throw new Error("접바둑은 9·13·19 로만 둘 수 있습니다");
    const 끝 = 크기 >= 13 ? 3 : 2, 가운데 = (크기 - 1) / 2, 먼 = 크기 - 1 - 끝;
    const 귀 = [[먼, 먼], [끝, 끝], [끝, 먼], [먼, 끝]];
    const 변 = [[가운데, 끝], [가운데, 먼], [먼, 가운데], [끝, 가운데]];
    수 = Math.min(수, 9);
    if (수 <= 4) return 귀.slice(0, 수);
    const 점 = [...귀];
    if (수 === 5 || 수 === 7 || 수 === 9) 점.push([가운데, 가운데]);
    return 점.concat(변.slice(0, 수 - 점.length));
  }

  /* 내장 봇 — engine.py 의 BuiltinBot 과 같은 판단을 한다. 아주 약하다. */
  class 내장봇 {
    constructor(씨앗 = 1) {
      this.이름 = "내장 봇";
      this.실력 = "아주 약함 (연습용)";
      this._씨 = 씨앗 >>> 0 || 1;
      this._마지막 = null;
    }

    _주사위() {                       // 씨앗 고정 난수 (xorshift)
      let x = this._씨;
      x ^= x << 13; x >>>= 0;
      x ^= x >> 17;
      x ^= x << 5; x >>>= 0;
      this._씨 = x;
      return x / 4294967296;
    }

    본다(색, 수) { if (수 !== null) this._마지막 = 수; }

    둘곳(판, 색) {
      const 후보 = 판.둘수있는곳(색).filter(수 => !this._내눈(판, 수, 색));
      if (!후보.length) return null;

      let 최선 = null, 최고 = -Infinity;
      for (const 수 of 후보) {
        const 점수 = this._점수(판, 수, 색) + this._주사위() * 0.4;
        if (점수 > 최고) { 최선 = 수; 최고 = 점수; }
      }
      if (최고 < 0.5 && 판.수순.length > 판.크기 * 판.크기 / 3) return null;
      return 최선;
    }

    _점수(판, 수, 색) {
      const 적 = 상대(색), 번호 = 판.번호(수);
      let 점수 = 0;

      for (const j of 판._이웃[번호]) {
        const 것 = 판.돌[j];
        if (것 === 빈칸) continue;
        const [모임, 활로] = 판.단위(j);
        if (것 === 적 && 활로.size === 1) 점수 += 12 + 2 * 모임.size;     // 따낸다
        else if (것 === 적 && 활로.size === 2) 점수 += 2.5;               // 단수
        else if (것 === 색 && 활로.size === 1) 점수 += 9 + 1.5 * 모임.size; // 살린다
        else if (것 === 색 && 활로.size === 2) 점수 += 1.5;               // 늘어둔다
      }

      판.돌[번호] = 색;
      const 뒤활로 = 판.단위(번호)[1].size;
      판.돌[번호] = 빈칸;
      점수 += 뒤활로 <= 1 ? -6 : Math.min(뒤활로, 4) * 0.5;

      const [행, 열] = 수, 크기 = 판.크기;
      const 가장자리 = Math.min(행, 열, 크기 - 1 - 행, 크기 - 1 - 열);
      if (판.수순.length < 크기) {                       // 포석엔 귀·변
        if (화점자리(크기).some(([r, c]) => r === 행 && c === 열)) 점수 += 4;
        if (가장자리 === 3) 점수 += 2;
      }
      if (가장자리 === 0) 점수 -= 3;                     // 1선은 피한다
      else if (가장자리 === 1) 점수 -= 1;

      if (this._마지막) {                                 // 상대 수 근처에 응수
        const 거리 = Math.abs(행 - this._마지막[0]) + Math.abs(열 - this._마지막[1]);
        if (거리 <= 3) 점수 += 2 - 거리 * 0.4;
      }
      return 점수;
    }

    _내눈(판, 수, 색) {
      const 번호 = 판.번호(수);
      for (const j of 판._이웃[번호]) if (판.돌[j] !== 색) return false;
      const [행, 열] = 수, 크기 = 판.크기, 적 = 상대(색);
      let 대각 = 0, 나쁨 = 0;
      for (const dr of [-1, 1]) for (const dc of [-1, 1]) {
        const r = 행 + dr, c = 열 + dc;
        if (r < 0 || c < 0 || r >= 크기 || c >= 크기) continue;
        대각++;
        if (판.돌[r * 크기 + c] === 적) 나쁨++;
      }
      return 대각 < 4 ? 나쁨 === 0 : 나쁨 <= 1;
    }
  }

  /* SGF 기보 */
  const _sgf글자 = "abcdefghijklmnopqrstuvwxyz";

  function sgf만들기(판, { 흑이름 = "흑", 백이름 = "백", 결과 = null } = {}) {
    const 점 = 수 => 수 === null ? "" : _sgf글자[수[1]] + _sgf글자[수[0]];
    const 감싸기 = 글 => String(글).replace(/\\/g, "\\\\").replace(/]/g, "\\]");
    const 머리 = [
      "GM[1]", "FF[4]", "CA[UTF-8]", "AP[baduk-web]",
      `SZ[${판.크기}]`, `KM[${판.덤}]`,
      `PB[${감싸기(흑이름)}]`, `PW[${감싸기(백이름)}]`,
      `DT[${new Date().toISOString().slice(0, 10)}]`,
    ];
    if (판.접바둑) {
      머리.push(`HA[${판.접바둑}]`);
      const 둔곳 = new Set(판.수순.filter(([c, m]) => m && c === 흑)
                            .map(([, m]) => m.join(",")));
      const 치석 = [];
      for (let i = 0; i < 판.돌.length; i++)
        if (판.돌[i] === 흑 && !둔곳.has(판.자리(i).join(","))) 치석.push(판.자리(i));
      if (치석.length)
        머리.push("AB" + 치석.slice(0, 판.접바둑).map(p => `[${점(p)}]`).join(""));
    }
    if (결과) 머리.push(`RE[${감싸기(결과)}]`);
    const 몸통 = 판.수순.map(([색, 수]) => `;${색 === 흑 ? "B" : "W"}[${점(수)}]`).join("");
    return "(;" + 머리.join("") + 몸통 + ")";
  }

  function sgf읽기(글) {
    글 = String(글).trim();
    if (!글.startsWith("(")) throw new Error("SGF 형식이 아닙니다");
    const 크기 = Number((글.match(/SZ\[(\d+)/) || [, 19])[1]);
    const 덤 = Number((글.match(/KM\[([\d.]+)/) || [, 6.5])[1]);
    const 판 = new 바둑판(크기, 덤);

    const 점풀기 = 값 => {
      if (!값 || 값.length < 2) return null;
      const 열 = _sgf글자.indexOf(값[0]), 행 = _sgf글자.indexOf(값[1]);
      if (열 < 0 || 행 < 0 || 열 >= 크기 || 행 >= 크기) return null;
      return [행, 열];
    };

    const 치석 = [...글.matchAll(/AB((?:\[[a-z]{0,2}\])+)/g)];
    if (치석.length) {
      const 점들 = [...치석[0][1].matchAll(/\[([a-z]{0,2})\]/g)]
        .map(m => 점풀기(m[1])).filter(Boolean);
      for (const p of 점들) 판.돌[판.번호(p)] = 흑;
      판.접바둑 = 점들.length;
      판.차례 = 백;
      판._본판 = new Set([판._열쇠()]);
    }

    for (const m of 글.matchAll(/;\s*([BW])\[([a-z]{0,2})\]/g))
      판.두기(점풀기(m[2]), m[1] === "B" ? 흑 : 백);
    return 판;
  }

  window.바둑 = {
    빈칸, 흑, 백, 바둑판, 내장봇, 위법수,
    상대, 색이름, 화점자리, 치석자리, sgf만들기, sgf읽기, 글자표,
  };

})();
