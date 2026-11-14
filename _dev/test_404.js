// 404.html 의 구제 스크립트: 대소문자·끝 / ·.html 이 틀린 주소를 정식 주소로 보낸다. 실패 시 exit 1.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', '404.html'), 'utf8');
const m = /<script>([\s\S]*?)<\/script>/.exec(html);
let bad = 0;
const ok = (c, msg) => { if (!c) { bad++; console.log('404: ' + msg); } };
ok(m, '구제 스크립트 없음');

function run(pathname, search = '', hash = '') {
  let to = null;
  vm.runInNewContext(m[1], { location: { pathname, search, hash, replace: (u) => { to = u; } }, decodeURI });
  return to;
}

const cases = [
  ['/absoluteear', '/AbsoluteEar/'],
  ['/absoluteear/', '/AbsoluteEar/'],
  ['/ABSOLUTEEAR/en', '/AbsoluteEar/en/'],
  ['/absoluteear/zh/index.html', '/AbsoluteEar/zh/'],
  ['/absoluteear/privacypolicy', '/AbsoluteEar/PrivacyPolicy'],
  ['/AbsoluteEar/PrivacyPolicy/', '/AbsoluteEar/PrivacyPolicy'],
  ['/absoluteear/termsofservice.html', '/AbsoluteEar/TermsOfService'],
  ['/absoluteear/get', '/AbsoluteEar/get/'],
  ['/get', '/get/'],
  ['/absoluteearpolicy.html', '/AbsoluteEarPolicy.html'],
  ['/termsofservice', '/termsOfService.html'],
  ['/absoluteear/no-such-page', '/AbsoluteEar/'],  // 앱 폴더 안의 모르는 주소 → 그 앱 첫 화면
  ['/pitchacademy/privacypolicy', '/PitchAcademy/PrivacyPolicy'],
  ['/PitchAcademy/PrivacyPolicy.html', '/PitchAcademy/PrivacyPolicy'],
  ['/pitchacademy/termsofservice/', '/PitchAcademy/TermsOfService'],
  ['/PitchAcademy/TermsOfService', null],
  ['/pitchacademy', null],                          // 첫 화면이 없는 앱 폴더는 보낼 곳이 없다(없는 주소로 보내지 않는다)
  ['/pitchacademy/no-such-page', null],
  ['/en/no-such-page', '/en/'],                     // 언어 폴더는 전처럼 그 언어 첫 화면으로
  ['/no-such-page', null],
  ['/AbsoluteEar/PrivacyPolicy', null],             // 이미 정식 주소면 다시 보내지 않는다(무한 이동 방지)
  ['/%E0%A4%A', null],                              // 깨진 인코딩에도 죽지 않는다
];
for (const [p, want] of cases) {
  let got;
  try { got = run(p); } catch (e) { got = 'THROW ' + e.message; }
  ok(got === want, `${p} → ${got} (기대 ${want})`);
}
ok(run('/absoluteear/', '?lang=en', '#faq') === '/AbsoluteEar/?lang=en#faq', '쿼리·해시를 유지하지 않음');
process.exit(bad ? 1 : 0);
