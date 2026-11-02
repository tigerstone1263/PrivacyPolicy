// lang.js 를 가짜 브라우저 환경에서 실행해 이동·안내 띠 규칙을 확인한다. 실패 시 exit 1.
// 규칙: 브라우저 언어만으로는 이동하지 않는다(검색 로봇이 한국어 주소를 리디렉션으로 보지 않게).
//       묶음의 한국어 주소(<html data-base>, 없으면 /)에서 브라우저 언어가 ko 가 아니면 그 언어 안내 띠를 보여 준다.
//       방문자가 직접 고른 언어(저장값·?lang=)만 이동 근거가 된다.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'assets', 'js', 'lang.js'), 'utf8');


function run({ path: p, langs, saved, search = '', blocked = false, base = null }) {
  let replaced = null;
  let shown = null;
  const listeners = {};
  const store = saved ? { 'ae-lang': saved } : {};
  const banner = {
    hidden: true,
    querySelectorAll: () => [],
    querySelector: () => null,
    setAttribute: (k, v) => { if (k === 'data-suggest') shown = v; },
    removeAttribute: () => {},
  };
  const ctx = {
    location: { pathname: p, search, hash: '', replace: (u) => { replaced = u; } },
    navigator: { languages: langs, language: langs[0] },
    localStorage: blocked
      ? { getItem: () => { throw new Error('SecurityError'); }, setItem: () => { throw new Error('SecurityError'); } }
      : { getItem: (k) => store[k] ?? null, setItem: (k, v) => { store[k] = v; } },
    document: {
      readyState: 'loading',
      addEventListener: (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); },
      getElementById: (id) => (id === 'lang-banner' ? banner : null),
      documentElement: { getAttribute: (k) => (k === 'data-base' ? base : null) },
    },
  };
  vm.runInNewContext(src, ctx);
  (listeners.DOMContentLoaded || []).forEach((fn) => fn());
  return { replaced, banner: banner.hidden ? null : shown };
}

const R = (replaced, banner = null) => ({ replaced, banner });
const cases = [
  [{ path: '/', langs: ['en-US'] }, R(null, 'en')],
  [{ path: '/', langs: ['zh-CN'] }, R(null, 'zh')],
  [{ path: '/', langs: ['ko-KR'] }, R(null)],
  [{ path: '/', langs: ['ja-JP'] }, R(null, 'en')],
  [{ path: '/', langs: ['ja-JP', 'ko-KR'] }, R(null)],
  [{ path: '/zh/', langs: ['en-US'] }, R(null)],
  [{ path: '/en/', langs: ['ko-KR'] }, R(null)],
  [{ path: '/', langs: ['en-US'], saved: 'ko' }, R(null)],
  [{ path: '/', langs: ['ko-KR'], saved: 'zh' }, R('/zh/')],
  [{ path: '/AbsoluteEarPolicy.html', langs: ['en-US'] }, R(null)],
  // 언어 링크는 ?lang= 을 달고 온다: 저장소가 막혀도, 새 탭으로 열어도 고른 언어가 이긴다
  [{ path: '/', langs: ['en-US'], search: '?lang=ko' }, R(null)],
  [{ path: '/', langs: ['en-US'], search: '?lang=ko', blocked: true }, R(null)],
  [{ path: '/', langs: ['en-US'], blocked: true }, R(null, 'en')],
  [{ path: '/', langs: ['ko-KR'], search: '?lang=zh' }, R('/zh/')],
  // 다른 쿼리(광고 태그 등)는 이동해도 유지하고 lang 만 뺀다
  [{ path: '/', langs: ['en-US'], search: '?utm_source=x' }, R(null, 'en')],
  [{ path: '/', langs: ['ko-KR'], search: '?lang=en&utm_source=x' }, R('/en/?utm_source=x')],
];
// 같은 규칙이 앱 폴더(/AbsoluteEar/)에서도 그대로: 경로·이동 대상에 앞부분만 붙는다
const AE = '/AbsoluteEar/';
const pre = (u) => (u && u.startsWith('/') ? AE + u.slice(1) : u);
const appCases = cases.map(([i, w]) => [{ ...i, base: AE, path: pre(i.path) }, R(pre(w.replaced), w.banner)]);
const cross = [
  // 루트 묶음의 스크립트는 앱 폴더 주소에서 아무것도 하지 않고, 반대도 같다
  [{ path: AE, langs: ['ko-KR'], saved: 'zh', base: '/' }, R(null)],
  [{ path: '/', langs: ['ko-KR'], saved: 'zh', base: AE }, R(null)],
  [{ path: '/', langs: ['ko-KR'], saved: 'en', base: '/' }, R('/en/')],
];
let bad = 0;
for (const [input, want] of [...cases, ...appCases, ...cross]) {
  const got = run(input);
  if (got.replaced !== want.replaced || got.banner !== want.banner) {
    bad++;
    console.log(`lang.js ${JSON.stringify(input)} → ${JSON.stringify(got)} (기대 ${JSON.stringify(want)})`);
  }
}
process.exit(bad ? 1 : 0);
