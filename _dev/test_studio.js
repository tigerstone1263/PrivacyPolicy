// 루트 페이지 연출(assets/js/studio.js)의 장면 값·영상 형식 선택을 DOM 없이 확인한다. 실패 시 exit 1.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'assets', 'js', 'studio.js'), 'utf8');
const ctx = {};
vm.runInNewContext(src, { window: ctx, globalThis: ctx });
const S = ctx.Studio;
let bad = 0;
const ok = (c, m) => { if (!c) { bad++; console.log('studio: ' + m); } };
ok(S, 'Studio 없음');

// 처음엔 글자가 붙어 있고 원은 닫혀 있고 폰은 아래에 숨어 있다
let f = S.frame(0);
ok(f.split === 0 && f.iris === 0 && f.rise === 0 && f.scene === 0, `p=0 → ${JSON.stringify(f)}`);
// 글자가 흩어지고 → 원이 열리고 → 폰이 다 올라온 뒤에 장면 1
ok(S.frame(0.12).split === 1, 'p=.12 에서 글자가 다 흩어지지 않음');
ok(S.frame(0.24).iris === 1, 'p=.24 에서 원이 다 열리지 않음');
ok(S.frame(0.32).rise === 1, 'p=.32 에서 폰이 다 올라오지 않음');
ok(S.SCENES[0] >= 0.32, '폰이 다 올라오기 전에 장면 1 이 시작됨');
// 장면 내내 원은 열려 있고, 마지막에 닫힌다(장면 글이 흰 바탕에 흰 글로 남지 않게)
for (const p of [0.34, 0.5, 0.7, 0.88]) ok(S.frame(p).iris === 1, `p=${p} 장면 중에 원이 닫힘`);
ok(S.frame(1).iris === 0, '끝에서 원이 닫히지 않음');
// 장면 순서와 경계
const scenes = [0, 0.2, 0.33, 0.34, 0.53, 0.54, 0.71, 0.72, 1].map((p) => S.frame(p).scene);
ok(JSON.stringify(scenes) === JSON.stringify([0, 0, 0, 1, 1, 2, 2, 3, 3]), `장면 경계 ${scenes}`);
// 음표는 장면 2 동안 흐르고, 길은 장면 3 에서 그려지며 점 4개가 차례로 켜진다
ok(S.frame(0.54).notes > 0 && S.frame(0.54).notes < 1 && S.frame(0.72).notes < 1, '음표가 장면 2 동안 흐르지 않음');
ok(S.frame(0.71).route === 0 && S.frame(0.88).route === 1 && S.frame(0.88).nodes === 4, '길이 장면 3 에서 그려지지 않음');
// 값은 0~1 로 막히고, iris 말고는 되돌아가지 않는다
let prev = S.frame(-1);
for (let p = -0.2; p <= 1.2; p += 0.01) {
  const g = S.frame(p);
  for (const k of ['split', 'iris', 'num', 'rise', 'notes', 'route']) ok(g[k] >= 0 && g[k] <= 1, `p=${p.toFixed(2)} ${k} 범위 밖 ${g[k]}`);
  for (const k of ['split', 'num', 'rise', 'notes', 'route', 'nodes', 'scene']) ok(g[k] >= prev[k], `p=${p.toFixed(2)} ${k} 값이 되돌아감`);
  prev = g;
}
// 반응: 장면 1 듣기, 장면 3 축하, 장면 2 는 idle (영상 파일이 있어야 한다)
ok(S.REACT[1] === 'listen' && S.REACT[3] === 'celebrate' && !S.REACT[2], `반응 ${JSON.stringify(S.REACT)}`);
for (const name of ['idle', 'wave', ...Object.values(S.REACT)]) {
  for (const ext of ['webm', 'mov']) {
    ok(fs.existsSync(path.join(__dirname, '..', 'assets', 'media', `sori-${name}.${ext}`)), `sori-${name}.${ext} 없음`);
  }
}
// 영상 형식: WebKit(사파리·iOS 모든 브라우저) → HEVC 알파 .mov, 나머지 → VP9 알파 .webm
const UA = {
  mac_safari: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15',
  mac_chrome: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
  mac_edge: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130.0 Safari/537.36 Edg/130.0',
  firefox: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:131.0) Gecko/20100101 Firefox/131.0',
  android: 'Mozilla/5.0 (Linux; Android 14; SM-S936N) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36',
  ios_chrome: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 CriOS/130.0 Mobile/15E148 Safari/604.1',
};
const want = { mac_safari: 'mov', mac_chrome: 'webm', mac_edge: 'webm', firefox: 'webm', android: 'webm', ios_chrome: 'mov' };
for (const [k, ua] of Object.entries(UA)) {
  const got = S.videoExt({ ios: k.startsWith('ios'), ua });
  ok(got === want[k], `${k} → ${got} (기대 ${want[k]})`);
}
ok(S.shouldEnable({ reduced: false }) && !S.shouldEnable({ reduced: true }), '동작 줄이기면 연출을 꺼야 함');
process.exit(bad ? 1 : 0);
