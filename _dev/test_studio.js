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

// 처음엔 글자가 붙어 있고 폰은 아래에 숨어 있다
let f = S.frame(0);
ok(f.split === 0 && f.rise === 0 && f.scene === 0, `p=0 → ${JSON.stringify(f)}`);
// 글자가 다 갈라진 뒤에 장면 1 이 시작된다 (폰이 다 올라온 뒤)
ok(S.frame(0.16).split === 1, 'p=.16 에서 글자가 다 갈라지지 않음');
ok(S.frame(0.26).rise === 1, 'p=.26 에서 폰이 다 올라오지 않음');
ok(S.SCENES[0] >= 0.26, '폰이 다 올라오기 전에 장면 1 이 시작됨');
// 장면 순서와 경계
const scenes = [0, 0.1, 0.27, 0.28, 0.5, 0.52, 0.75, 0.76, 1].map((p) => S.frame(p).scene);
ok(JSON.stringify(scenes) === JSON.stringify([0, 0, 0, 1, 1, 2, 2, 3, 3]), `장면 경계 ${scenes}`);
// 값은 0~1 로 막히고 단조 증가
let prev = { split: 0, rise: 0, scene: 0 };
for (let p = -0.2; p <= 1.2; p += 0.01) {
  const g = S.frame(p);
  ok(g.split >= 0 && g.split <= 1 && g.rise >= 0 && g.rise <= 1, `p=${p.toFixed(2)} 범위 밖 ${JSON.stringify(g)}`);
  ok(g.split >= prev.split && g.rise >= prev.rise && g.scene >= prev.scene, `p=${p.toFixed(2)} 값이 되돌아감`);
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
