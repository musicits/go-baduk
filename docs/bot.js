/* 몬테카를로 탐색(MCTS) 바둑 봇.
 *
 * 수를 실제로 읽는다. 한 수를 둘 때마다 그 자리에서 대국을 끝까지
 * 무작위로 두어 보고(플레이아웃), 이기는 비율이 높은 자리를 고른다.
 * 이것을 정해진 시간 동안 수만 번 반복한다.
 *
 * KataGo 같은 신경망은 없지만, 규칙만으로도 "따먹기만 하는" 봇보다는
 * 훨씬 낫다. 특히 9로에서 차이가 크다.
 *
 * 웹 워커에서 돌린다. 그래야 탐색하는 동안 화면이 안 멈춘다.
 * rules.js 와 따로 구현한 이유는 속도다. 여기서는 Set 이나 객체를
 * 만들지 않고 타입 배열만 쓴다. 초당 수천 번 돌아야 하기 때문이다.
 */
"use strict";

(function (뿌리) {

  const 빈칸 = 0, 흑 = 1, 백 = 2;
  const 패스 = -1;

  /* ------------------------------------------------------------------
   * 빠른 바둑판. 탐색 전용이라 되돌리기나 기보 같은 건 없다.
   * ------------------------------------------------------------------ */
  class 빠른판 {
    constructor(크기) {
      this.크기 = 크기;
      this.칸수 = 크기 * 크기;
      this.돌 = new Int8Array(this.칸수);
      this.패자리 = -1;
      this.차례 = 흑;
      this.따낸 = [0, 0, 0];

      // 이웃을 미리 펼쳐 둔다. [자리*4 + n] 에 이웃 번호, 없으면 -1.
      this.이웃 = new Int32Array(this.칸수 * 4).fill(-1);
      for (let i = 0; i < this.칸수; i++) {
        const 행 = (i / 크기) | 0, 열 = i % 크기;
        let n = i * 4;
        if (행 > 0) this.이웃[n++] = i - 크기;
        if (행 < 크기 - 1) this.이웃[n++] = i + 크기;
        if (열 > 0) this.이웃[n++] = i - 1;
        if (열 < 크기 - 1) this.이웃[n++] = i + 1;
      }

      // 물길 찾기용 임시 배열. 매번 새로 만들지 않고 도장(_도장)으로 구분한다.
      this._표시 = new Int32Array(this.칸수);
      this._도장 = 0;
      this._쌓기 = new Int32Array(this.칸수);
      this._모임 = new Int32Array(this.칸수);
      this._섞기 = new Int32Array(this.칸수);
      for (let i = 0; i < this.칸수; i++) this._섞기[i] = i;
    }

    베끼기(딴판) {
      딴판.돌.set(this.돌);
      딴판.패자리 = this.패자리;
      딴판.차례 = this.차례;
      딴판.따낸[흑] = this.따낸[흑];
      딴판.따낸[백] = this.따낸[백];
      return 딴판;
    }

    /* 한 단위의 돌과 활로를 센다.
     * 활로가 0 이면 잡힌 것이다. 모인 돌은 this._모임 앞쪽에 담긴다. */
    _단위(시작) {
      const 색 = this.돌[시작];
      const 도장 = ++this._도장;
      let 쌓기수 = 0, 모임수 = 0, 활로 = 0;
      this._쌓기[쌓기수++] = 시작;
      this._표시[시작] = 도장;

      while (쌓기수) {
        const i = this._쌓기[--쌓기수];
        this._모임[모임수++] = i;
        const 밑 = i * 4;
        for (let n = 0; n < 4; n++) {
          const j = this.이웃[밑 + n];
          if (j < 0) break;
          if (this._표시[j] === 도장) continue;
          const 것 = this.돌[j];
          if (것 === 빈칸) { this._표시[j] = 도장; 활로++; }
          else if (것 === 색) { this._표시[j] = 도장; this._쌓기[쌓기수++] = j; }
        }
      }
      this._모임수 = 모임수;
      return 활로;
    }

    /* 그 자리에 둘 수 있으면 두고 true. 규칙에 어긋나면 아무것도 안 하고 false. */
    두기(자리, 색) {
      if (자리 === 패스) {
        this.패자리 = -1;
        this.차례 = 색 === 흑 ? 백 : 흑;
        return true;
      }
      if (this.돌[자리] !== 빈칸 || 자리 === this.패자리) return false;

      const 적 = 색 === 흑 ? 백 : 흑;
      const 밑 = 자리 * 4;
      this.돌[자리] = 색;

      let 잡은수 = 0, 마지막잡은 = -1;
      for (let n = 0; n < 4; n++) {
        const j = this.이웃[밑 + n];
        if (j < 0) break;
        if (this.돌[j] !== 적) continue;
        if (this._단위(j) === 0) {
          for (let m = 0; m < this._모임수; m++) {
            마지막잡은 = this._모임[m];
            this.돌[마지막잡은] = 빈칸;
          }
          잡은수 += this._모임수;
        }
      }

      if (잡은수 === 0 && this._단위(자리) === 0) {
        this.돌[자리] = 빈칸;              // 자살수
        return false;
      }

      this.따낸[색] += 잡은수;
      // 한 점만 따냈고 내 돌도 한 점 단수면 그 자리가 패다.
      this.패자리 = -1;
      if (잡은수 === 1) {
        if (this._단위(자리) === 1 && this._모임수 === 1) this.패자리 = 마지막잡은;
      }
      this.차례 = 적;
      return true;
    }

    /* 자기 눈이면 true. 메우면 스스로 죽으니 플레이아웃에서 피한다. */
    내눈인가(자리, 색) {
      const 밑 = 자리 * 4;
      let 이웃수 = 0;
      for (let n = 0; n < 4; n++) {
        const j = this.이웃[밑 + n];
        if (j < 0) break;
        이웃수++;
        if (this.돌[j] !== 색) return false;
      }
      const 크기 = this.크기;
      const 행 = (자리 / 크기) | 0, 열 = 자리 % 크기;
      const 적 = 색 === 흑 ? 백 : 흑;
      let 대각 = 0, 나쁨 = 0;
      for (let dr = -1; dr <= 1; dr += 2) {
        for (let dc = -1; dc <= 1; dc += 2) {
          const r = 행 + dr, c = 열 + dc;
          if (r < 0 || c < 0 || r >= 크기 || c >= 크기) continue;
          대각++;
          if (this.돌[r * 크기 + c] === 적) 나쁨++;
        }
      }
      return 대각 < 4 ? 나쁨 === 0 : 나쁨 <= 1;
    }

    /* 중국식(돌+집)으로 흑이 이겼는지 본다. 플레이아웃 끝에서 쓴다. */
    흑이이겼나(덤) {
      let 흑점 = 0, 백점 = 0;
      const 도장기준 = this._도장;
      for (let i = 0; i < this.칸수; i++) {
        const 것 = this.돌[i];
        if (것 === 흑) { 흑점++; continue; }
        if (것 === 백) { 백점++; continue; }
        // 빈 자리는 붙어 있는 돌 색으로 주인을 정한다.
        let 흑닿음 = false, 백닿음 = false;
        const 밑 = i * 4;
        for (let n = 0; n < 4; n++) {
          const j = this.이웃[밑 + n];
          if (j < 0) break;
          if (this.돌[j] === 흑) 흑닿음 = true;
          else if (this.돌[j] === 백) 백닿음 = true;
        }
        if (흑닿음 && !백닿음) 흑점++;
        else if (백닿음 && !흑닿음) 백점++;
      }
      this._도장 = 도장기준;
      return 흑점 > 백점 + 덤;
    }

    /* 끝까지 아무렇게나 두어 본다. 흑이 이기면 true. */
    플레이아웃(덤, 난수) {
      const 최대수 = this.칸수 * 2;
      let 연속패스 = 0;
      for (let 수 = 0; 수 < 최대수 && 연속패스 < 2; 수++) {
        const 색 = this.차례;
        let 둔곳 = -1;

        // 빈 자리를 무작위 순서로 훑어서 처음 되는 곳에 둔다.
        const 시작 = (난수() * this.칸수) | 0;
        for (let k = 0; k < this.칸수; k++) {
          const 자리 = (시작 + k) % this.칸수;
          if (this.돌[자리] !== 빈칸) continue;
          if (this.내눈인가(자리, 색)) continue;
          if (this.두기(자리, 색)) { 둔곳 = 자리; break; }
        }

        if (둔곳 < 0) { this.두기(패스, 색); 연속패스++; }
        else 연속패스 = 0;
      }
      return this.흑이이겼나(덤);
    }
  }

  /* ------------------------------------------------------------------
   * MCTS
   * ------------------------------------------------------------------ */
  function 난수생성기(씨앗) {
    let x = (씨앗 >>> 0) || 12345;
    return function () {
      x ^= x << 13; x >>>= 0;
      x ^= x >> 17;
      x ^= x << 5; x >>>= 0;
      return x / 4294967296;
    };
  }

  const 탐험상수 = 1.2;

  function 마디(수, 둔색) {
    // 안펼침이 null 이면 "아직 후보를 안 뽑아봤다" 는 뜻이다.
    return { 수, 둔색, 방문: 0, 이김: 0, 자식: [], 안펼침: null };
  }

  function 후보모으기(판, 색) {
    const 목록 = [];
    for (let i = 0; i < 판.칸수; i++) {
      if (판.돌[i] !== 빈칸) continue;
      if (판.내눈인가(i, 색)) continue;
      목록.push(i);
    }
    return 목록;
  }

  /** 한 수를 고른다.
   * @param {Int8Array} 돌 현재 판
   * @param {number} 크기 판 크기
   * @param {number} 색 둘 색
   * @param {number} 덤
   * @param {number} 패자리 되따내기가 막힌 자리 (-1 이면 없음)
   * @param {number} 시간예산 밀리초
   * @returns {{수, 승률, 후보들, 플레이아웃수}}
   */
  function 생각하기(돌, 크기, 색, 덤, 패자리, 시간예산, 씨앗) {
    const 난수 = 난수생성기(씨앗 || 20260827);
    const 본판 = new 빠른판(크기);
    본판.돌.set(돌);
    본판.차례 = 색;
    본판.패자리 = 패자리 == null ? -1 : 패자리;

    const 뿌리마디 = 마디(패스, 색 === 흑 ? 백 : 흑);
    뿌리마디.안펼침 = 후보모으기(본판, 색);
    if (!뿌리마디.안펼침.length)
      return { 수: 패스, 승률: 0.5, 후보들: [], 플레이아웃수: 0 };

    const 작업판 = new 빠른판(크기);
    const 길 = [];
    const 끝시각 = Date.now() + 시간예산;
    let 횟수 = 0;

    while (true) {
      if ((횟수 & 31) === 0 && Date.now() > 끝시각) break;
      횟수++;

      본판.베끼기(작업판);
      길.length = 0;
      let 현재 = 뿌리마디;
      길.push(현재);

      // 1) 내려가기 — 이미 펼친 가지 중 UCT 가 가장 큰 곳으로
      while (현재.안펼침 !== null && 현재.안펼침.length === 0
             && 현재.자식.length) {
        let 고른 = null, 최고 = -Infinity;
        const 로그 = Math.log(현재.방문 + 1);
        for (const 자식 of 현재.자식) {
          const 값 = 자식.방문 === 0 ? 1e6
            : 자식.이김 / 자식.방문 + 탐험상수 * Math.sqrt(로그 / 자식.방문);
          if (값 > 최고) { 최고 = 값; 고른 = 자식; }
        }
        if (!고른) break;
        작업판.두기(고른.수, 고른.둔색);
        현재 = 고른;
        길.push(현재);
      }

      // 2) 넓히기 — 아직 안 둬 본 자리 하나를 새로 연다
      if (현재.안펼침 === null) 현재.안펼침 = 후보모으기(작업판, 작업판.차례);
      if (현재.안펼침.length) {
        const 뽑기 = (난수() * 현재.안펼침.length) | 0;
        const 자리 = 현재.안펼침[뽑기];
        현재.안펼침[뽑기] = 현재.안펼침[현재.안펼침.length - 1];
        현재.안펼침.pop();
        const 둘색 = 작업판.차례;
        if (작업판.두기(자리, 둘색)) {
          const 새마디 = 마디(자리, 둘색);
          현재.자식.push(새마디);
          현재 = 새마디;
          길.push(현재);
        }
      }

      // 3) 끝까지 두어 보고  4) 결과를 되돌려 반영
      const 흑승 = 작업판.플레이아웃(덤, 난수);
      for (const 마디하나 of 길) {
        마디하나.방문++;
        const 이김 = (마디하나.둔색 === 흑) === 흑승;
        if (이김) 마디하나.이김++;
      }
    }

    if (!뿌리마디.자식.length)
      return { 수: 패스, 승률: 0.5, 후보들: [], 플레이아웃수: 횟수 };

    // 가장 많이 둬 본 자리를 고른다 (승률보다 방문수가 안정적이다)
    const 순서 = 뿌리마디.자식.slice().sort((a, b) => b.방문 - a.방문);
    const 으뜸 = 순서[0];
    const 승률 = 으뜸.방문 ? 으뜸.이김 / 으뜸.방문 : 0.5;

    // 승률이 너무 낮으면 던지지 말고 패스로 마무리를 노린다
    const 후보들 = 순서.slice(0, 5).map(자식 => ({
      수: 자식.수,
      승률: 자식.방문 ? 자식.이김 / 자식.방문 : 0,
      방문수: 자식.방문,
    }));

    return { 수: 으뜸.수, 승률, 후보들, 플레이아웃수: 횟수 };
  }

  뿌리.바둑봇 = { 생각하기, 빠른판, 패스, 흑, 백, 빈칸 };

  // 웹 워커로 불렸을 때: 메시지를 받아 생각하고 결과를 돌려준다.
  if (typeof self !== "undefined" && typeof self.postMessage === "function"
      && typeof window === "undefined") {
    self.onmessage = function (사건) {
      const d = 사건.data;
      try {
        const 답 = 생각하기(new Int8Array(d.돌), d.크기, d.색, d.덤,
                          d.패자리, d.시간, d.씨앗);
        self.postMessage({ 성공: true, ...답, 표: d.표 });
      } catch (오류) {
        self.postMessage({ 성공: false, 오류: String(오류), 표: d.표 });
      }
    };
  }

})(typeof self !== "undefined" ? self : globalThis);
