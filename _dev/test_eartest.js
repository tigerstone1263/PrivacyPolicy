// 청음 맛보기(assets/js/eartest.js)의 문제 생성·채점 로직을 DOM 없이 확인한다. 실패 시 exit 1.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'assets', 'js', 'eartest.js'), 'utf8');
const ctx = {};
ctx.window = ctx;
vm.runInNewContext(src, ctx);
const T = ctx.EarTest;
let bad = 0;
const ok = (cond, msg) => { if (!cond) { bad++; console.log('eartest: ' + msg); } };

ok(T, 'EarTest 가 노출되지 않음');
if (T) {
  // 주파수: A4=440Hz, A3=220Hz, C4≈261.63Hz
  ok(Math.abs(T.midiToHz(69) - 440) < 1e-9, 'A4 != 440');
  ok(Math.abs(T.midiToHz(57) - 220) < 1e-9, 'A3 != 220');
  ok(Math.abs(T.midiToHz(60) - 261.6256) < 1e-3, 'C4 != 261.63');
  // 앱과 같은 세 음정: 장3도(4), 완전4도(5), 완전5도(7). 키 이름은 앱과 같이 maj3/p4/p5
  const semis = T.INTERVALS.map(i => i.key + ':' + i.semi).join(',');
  ok(semis === 'maj3:4,p4:5,p5:7', '음정 집합이 장3도·완전4도·완전5도가 아님: ' + semis);
  // 한 판(3문제): 문제마다 따로 뽑아 소거법으로 풀리지 않게, 바로 앞 문제와 같은 음정은 피한다
  let seed = 7;
  const rand = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  const seenThird = new Set();
  for (let n = 0; n < 400; n++) {
    const round = T.makeRound(rand);
    ok(round.length === T.ROUNDS && T.ROUNDS === 3, '한 판이 3문제가 아님');
    for (let i = 1; i < round.length; i++) ok(round[i].answer !== round[i - 1].answer, '바로 앞 문제와 같은 음정');
    const k = round.map(q => q.answer);
    if (k[0] !== k[1]) seenThird.add(k[2] === k[0] ? 'repeat-first' : 'third-kind');
    for (const q of round) {
      ok(q.root >= 55 && q.root <= 67, '근음 범위 밖: ' + q.root);
      const iv = T.INTERVALS.find(i => i.key === q.answer);
      ok(iv && q.top - q.root === iv.semi, '정답과 음 간격 불일치');
      ok(T.grade(q, q.answer) === true, '정답 채점 실패');
      ok(T.INTERVALS.filter(i => i.key !== q.answer).every(i => T.grade(q, i.key) === false), '오답이 정답 처리됨');
    }
  }
  // 3번 문제가 1·2번과 다른 '남은 음정'으로만 나오면 소거법으로 풀린다 — 두 경우가 모두 나와야 한다
  ok(seenThird.has('repeat-first') && seenThird.has('third-kind'), '3번 문제가 소거법으로 풀림: ' + [...seenThird]);
}
process.exit(bad ? 1 : 0);
