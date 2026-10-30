// 기기 판별(템플릿 head 의 #os-detect)과 /get/ 이동 규칙을 확인한다. 실패 시 exit 1.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.join(__dirname, '..');
let bad = 0;
const ok = (c, m) => { if (!c) { bad++; console.log('os: ' + m); } };
const UA = {
  iphone: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148',
  ipad13: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15',
  android: 'Mozilla/5.0 (Linux; Android 14; SM-S936N) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36',
  mac: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130.0 Safari/537.36',
  win: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36',
};
const touch = { ipad13: 5 };

// 1) 페이지 head 의 판별 스크립트: <html> 에 os-ios / os-android 클래스
const tpl = fs.readFileSync(path.join(root, '_dev', 'template.html'), 'utf8');
const m = /<script id="os-detect">([\s\S]*?)<\/script>/.exec(tpl);
ok(m, '#os-detect 스크립트 없음');
const want = { iphone: 'os-ios', ipad13: 'os-ios', android: 'os-android', mac: '', win: '' };
if (m) for (const [k, ua] of Object.entries(UA)) {
  const cls = new Set();
  vm.runInNewContext(m[1], {
    navigator: { userAgent: ua, maxTouchPoints: touch[k] || 0 },
    document: { documentElement: { classList: { add: (...c) => c.forEach(x => cls.add(x)) } } },
  });
  const os = [...cls].find(c => c.startsWith('os-')) || '';
  ok(os === want[k], `${k} → '${os}' (기대 '${want[k]}')`);
  ok(cls.has('js'), `${k}: js 클래스 없음`);
}

// 2) /get/ : iOS → App Store, Android → Google Play(utm_campaign=qr), 그 외는 이동하지 않음
const getHtml = fs.readFileSync(path.join(root, 'get', 'index.html'), 'utf8');
const g = /<script>([\s\S]*?)<\/script>/.exec(getHtml);
ok(g, '/get/ 이동 스크립트 없음');
if (g) for (const [k, ua] of Object.entries(UA)) {
  let to = null;
  vm.runInNewContext(g[1], { navigator: { userAgent: ua, maxTouchPoints: touch[k] || 0 }, location: { replace: (u) => { to = u; } } });
  const exp = k === 'android' ? 'play.google.com' : (k === 'iphone' || k === 'ipad13') ? 'apps.apple.com' : null;
  ok(exp ? (to || '').includes(exp) : to === null, `/get/ ${k} → ${to}`);
  if (k === 'android') ok((to || '').includes('utm_campaign%3Dqr'), 'Play 이동에 utm_campaign=qr 없음');
}
process.exit(bad ? 1 : 0);
