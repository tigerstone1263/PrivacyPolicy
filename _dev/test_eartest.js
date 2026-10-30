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
  // 앱과 같은 세 음정: 장3도(4), 완전4도(5), 완전5도(7)
  const semis = T.INTERVALS.map(i => i.semi).join(',');
  ok(semis === '4,5,7', '음정 집합이 장3도·완전4도·완전5도가 아님: ' + semis);
  // 한 판(3문제)은 세 음정을 한 번씩, 근음은 G3~G4, 정답 키는 실제 반음 수와 일치
  let seed = 7;
  const rand = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  for (let n = 0; n < 200; n++) {
    const round = T.makeRound(rand);
    ok(round.length === T.ROUNDS && T.ROUNDS === 3, '한 판이 3문제가 아님');
    const keys = round.map(q => q.answer).sort().join(',');
    ok(keys === 'm3,p4,p5', '한 판에 음정이 겹침: ' + keys);
    for (const q of round) {
      ok(q.root >= 55 && q.root <= 67, '근음 범위 밖: ' + q.root);
      const iv = T.INTERVALS.find(i => i.key === q.answer);
      ok(iv && q.top - q.root === iv.semi, '정답과 음 간격 불일치');
      ok(T.grade(q, q.answer) === true, '정답 채점 실패');
      ok(T.INTERVALS.filter(i => i.key !== q.answer).every(i => T.grade(q, i.key) === false), '오답이 정답 처리됨');
    }
  }
}
process.exit(bad ? 1 : 0);
