// lang.js 를 가짜 브라우저 환경에서 실행해 이동 규칙을 확인한다. 실패 시 exit 1.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'assets', 'js', 'lang.js'), 'utf8');

function run({ path: p, langs, saved, search = '', blocked = false }) {
  let replaced = null;
  const store = saved ? { 'ae-lang': saved } : {};
  const ctx = {
    location: { pathname: p, search, hash: '', replace: (u) => { replaced = u; } },
    navigator: { languages: langs, language: langs[0] },
    localStorage: blocked
      ? { getItem: () => { throw new Error('SecurityError'); }, setItem: () => { throw new Error('SecurityError'); } }
      : { getItem: (k) => store[k] ?? null, setItem: (k, v) => { store[k] = v; } },
    document: { addEventListener: () => {} },
  };
  vm.runInNewContext(src, ctx);
  return replaced;
}

const cases = [
  [{ path: '/', langs: ['en-US'] }, '/en/'],
  [{ path: '/', langs: ['zh-CN'] }, '/zh/'],
  [{ path: '/', langs: ['ko-KR'] }, null],
  [{ path: '/', langs: ['ja-JP'] }, '/en/'],
  [{ path: '/', langs: ['ja-JP', 'ko-KR'] }, null],
  [{ path: '/zh/', langs: ['en-US'] }, null],
  [{ path: '/en/', langs: ['ko-KR'] }, null],
  [{ path: '/', langs: ['en-US'], saved: 'ko' }, null],
  [{ path: '/', langs: ['ko-KR'], saved: 'zh' }, '/zh/'],
  [{ path: '/AbsoluteEarPolicy.html', langs: ['en-US'] }, null],
  // 언어 링크는 ?lang= 을 달고 온다: 저장소가 막혀도, 새 탭으로 열어도 고른 언어가 이긴다
  [{ path: '/', langs: ['en-US'], search: '?lang=ko' }, null],
  [{ path: '/', langs: ['en-US'], search: '?lang=ko', blocked: true }, null],
  [{ path: '/', langs: ['en-US'], blocked: true }, '/en/'],
  [{ path: '/', langs: ['ko-KR'], search: '?lang=zh' }, '/zh/'],
  // 다른 쿼리(광고 태그 등)는 이동해도 유지하고 lang 만 뺀다
  [{ path: '/', langs: ['en-US'], search: '?utm_source=x' }, '/en/?utm_source=x'],
  [{ path: '/', langs: ['ko-KR'], search: '?lang=en&utm_source=x' }, '/en/?utm_source=x'],
];
let bad = 0;
for (const [input, want] of cases) {
  const got = run(input);
  if (got !== want) { bad++; console.log(`lang.js ${JSON.stringify(input)} → ${got} (기대 ${want})`); }
}
process.exit(bad ? 1 : 0);
