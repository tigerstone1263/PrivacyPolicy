// lang.js 를 가짜 브라우저 환경에서 실행해 이동 규칙을 확인한다. 실패 시 exit 1.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'assets', 'js', 'lang.js'), 'utf8');

function run({ path: p, langs, saved }) {
  let replaced = null;
  const store = saved ? { 'ae-lang': saved } : {};
  const ctx = {
    location: { pathname: p, search: '', hash: '', replace: (u) => { replaced = u; } },
    navigator: { languages: langs, language: langs[0] },
    localStorage: { getItem: (k) => store[k] ?? null, setItem: (k, v) => { store[k] = v; } },
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
];
let bad = 0;
for (const [input, want] of cases) {
  const got = run(input);
  if (got !== want) { bad++; console.log(`lang.js ${JSON.stringify(input)} → ${got} (기대 ${want})`); }
}
process.exit(bad ? 1 : 0);
