// 첫 화면 스크롤 연출(AbsoluteEar/assets/js/cine.js)의 켜짐 조건과 장면 값을 DOM 없이 확인한다. 실패 시 exit 1.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'AbsoluteEar', 'assets', 'js', 'cine.js'), 'utf8');
const ctx = {}; ctx.window = ctx;
vm.runInNewContext(src, ctx);
const C = ctx.Cine;
let bad = 0;
const ok = (c, m) => { if (!c) { bad++; console.log('cine: ' + m); } };
ok(C, 'Cine 이 노출되지 않음');
if (C) {
  // 켜짐 조건: 넓은 화면 + 마우스 + 동작 줄이기 아님
  ok(C.shouldEnable({ width: 1280, hover: true, reduced: false }) === true, '데스크톱인데 꺼짐');
  ok(C.shouldEnable({ width: 1280, hover: true, reduced: true }) === false, '동작 줄이기인데 켜짐');
  ok(C.shouldEnable({ width: 800, hover: true, reduced: false }) === false, '좁은 화면인데 켜짐');
  ok(C.shouldEnable({ width: 1024, hover: true, reduced: false }) === false, '좌우 배치가 안 되는 1024px 에서 켜짐');
  ok(C.shouldEnable({ width: 1100, hover: true, reduced: false }) === true, '1100px 에서 꺼짐');
  ok(C.shouldEnable({ width: 1280, hover: false, reduced: false }) === false, '터치 기기인데 켜짐');
  // 장면: 시작(0)은 정적인 첫 화면과 같고, 끝(RUNWAY)은 연출이 끝난 상태
  const a = C.frame(0), z = C.frame(C.RUNWAY);
  ok(a.copyO === 1 && a.copyY === 0, '시작 장면에서 문구가 이미 움직임');
  ok(a.frontRot === -4 && a.frontS === 1 && a.capO === 0, '시작 장면이 정적 첫 화면과 다름');
  ok(z.copyO === 0, '끝 장면에서 문구가 남음');
  ok(z.frontRot === 0 && z.frontS > 1.05, '끝 장면에서 폰이 바로 서서 다가오지 않음');
  ok(z.capO === 1, '끝 장면에서 자막이 안 보임');
  ok(z.wordS > a.wordS && z.wordY < a.wordY, '워드마크가 떠오르며 커지지 않음');
  // 단조성: 스크롤이 늘면 문구 투명도는 줄고 자막 투명도는 는다
  let prev = C.frame(0);
  for (let s = 20; s <= C.RUNWAY; s += 20) {
    const f = C.frame(s);
    ok(f.copyO <= prev.copyO + 1e-9 && f.capO >= prev.capO - 1e-9, '장면 값이 거꾸로 움직임 @' + s);
    prev = f;
  }
  // 범위 밖은 끝값에 고정
  ok(JSON.stringify(C.frame(-100)) === JSON.stringify(a) && JSON.stringify(C.frame(C.RUNWAY + 500)) === JSON.stringify(z), '범위 밖 값이 고정되지 않음');
}
process.exit(bad ? 1 : 0);
