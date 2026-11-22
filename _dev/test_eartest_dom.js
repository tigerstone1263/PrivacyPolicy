// 청음 맛보기를 가짜 DOM·가짜 오디오로 클릭 순서대로 돌려 본다 (리뷰 I1·I2·C1·M1·M9 회귀 방지). 실패 시 exit 1.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'assets', 'js', 'eartest.js'), 'utf8');
let bad = 0;
const ok = (c, m) => { if (!c) { bad++; console.log('eartest-dom: ' + m); } };

function classList() { const s = new Set(); return { add: (...c) => c.forEach(x => s.add(x)), remove: (...c) => c.forEach(x => s.delete(x)), contains: (c) => s.has(c), _s: s }; }
function makeDom() {
  const doc = { activeElement: null };
  const el = (attrs = {}) => {
    const e = { attrs, classList: classList(), textContent: '', disabled: false, hidden: false, src: '', listeners: {},
      addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); },
      click() { if (this.disabled) return; (this.listeners.click || []).forEach(fn => fn()); },
      focus() { doc.activeElement = this; },
      getAttribute(k) { return this.attrs[k]; }, setAttribute(k, v) { this.attrs[k] = String(v); } };
    return e;
  };
  const opts = ['maj3', 'p4', 'p5'].map((k, i) => { const b = el({ 'data-iv': k }); b.textContent = ['장3도', '완전4도', '완전5도'][i]; b.disabled = true; return b; });
  const parts = {
    '.try-stage img': el(), '.try-progress': el(), '.try-play': el(), '.try-play .lbl': el(), '.try-play .ico': el(),
    '.try-feedback': el(), '.try-next': el(), '.try-done': el(), '.try-done-text': el(), '.try-retry': el(), '.try-more': el(),
  };
  parts['.try-next'].hidden = true; parts['.try-done'].hidden = true; parts['.try-more'].textContent = '앱에서는…';
  const sec = { classList: classList(), dataset: {
      q: '문제 {n} / 3', correct: '정답이에요!', wrong: '아쉬워요. 정답은 {a}였어요.', result: '3문제 중 {k}문제를 맞혔어요.',
      perfect: '완벽해요!', zero: '아직 맞힌 문제가 없어요.', keep: '처음엔 누구나…', play: '듣기', replay: '다시 듣기',
      frameIdle: 'idle', frameListen: 'listen', frameYes: 'yes', frameNo: 'no' },
    querySelector: (s) => parts[s] || null, querySelectorAll: (s) => (s === 'button[data-iv]' ? opts : []) };
  return { doc, sec, parts, opts };
}
function makeAudio() {
  const made = [];
  function Ctx() {
    const ctx = { currentTime: 0, state: 'running', destination: {}, oscs: [], suspends: 0, resumes: 0,
      createGain() { const g = { disconnected: false, gain: { value: 1, setValueAtTime() {}, exponentialRampToValueAtTime() {}, setTargetAtTime() {}, cancelScheduledValues() {}, linearRampToValueAtTime() {} }, connect() {}, disconnect() { g.disconnected = true; } }; return g; },
      createOscillator() { const o = { type: '', frequency: { value: 0 }, connect() {}, start(t) { o.t0 = t; }, stop(t) { o.t1 = t; }, onended: null }; ctx.oscs.push(o); return o; },
      resume() { ctx.resumes++; ctx.state = 'running'; return Promise.resolve(); },
      suspend() { ctx.suspends++; ctx.state = 'suspended'; return Promise.resolve(); } };
    made.push(ctx); return ctx;
  }
  return { Ctx, made };
}
function makeTimers() {
  let q = []; let id = 0;
  return { setTimeout: (fn, ms) => { q.push({ id: ++id, fn, ms }); return id; }, clearTimeout: (i) => { q = q.filter(t => t.id !== i); }, flush: () => { const run = q; q = []; run.forEach(t => t.fn()); } };
}
function load(env) {
  const ctx = { window: {} }; ctx.window = ctx;
  vm.runInNewContext(src, ctx);
  return ctx.EarTest;
}
const T = load();
ok(T && typeof T.mount === 'function', 'EarTest.mount 이 없음');
if (!T || !T.mount) process.exit(1);

// 결정적인 판: maj3 → p4 → p5
let seed = 3; const rand = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
function setup(extra = {}) {
  const dom = makeDom(); const audio = makeAudio(); const timers = makeTimers();
  const env = Object.assign({ AudioContext: audio.Ctx, setTimeout: timers.setTimeout, clearTimeout: timers.clearTimeout, random: rand,
    navigator: { userAgent: 'Mozilla/5.0 (Macintosh)', maxTouchPoints: 0 }, document: dom.doc }, extra);
  const app = T.mount(dom.sec, env);
  return { dom, audio, timers, app, env };
}
const enabledCount = (dom) => dom.opts.filter(b => !b.disabled).length;
const lastOsc = (audio) => { const c = audio.made[audio.made.length - 1]; return c.oscs[c.oscs.length - 1]; };
const endLatest = (audio) => { const o = lastOsc(audio); o.onended && o.onended(); };

// 1) 기본 흐름: 듣기 전엔 잠김, 소리가 끝나야 열림, 끝나면 오디오를 쉬게 함
{
  const { dom, audio, app } = setup();
  ok(dom.sec.classList.contains('try-ready'), 'Web Audio 가 있는데 try-ready 가 아님');
  ok(enabledCount(dom) === 0, '듣기 전에 보기가 열림');
  dom.parts['.try-play'].click();
  const c = audio.made[0];
  ok(c && c.oscs.length > 0, '듣기를 눌렀는데 음이 예약되지 않음');
  ok(dom.parts['.try-stage img'].src === 'listen', '듣는 중 표정이 아님');
  ok(enabledCount(dom) === 0, '소리가 끝나기 전에 보기가 열림');
  endLatest(audio);
  ok(enabledCount(dom) === 3, '소리가 끝났는데 보기가 안 열림');
  ok(c.suspends >= 1, '소리가 끝났는데 오디오를 쉬게 하지 않음');
  ok(dom.parts['.try-stage img'].src === 'idle', '소리가 끝난 뒤 기본 표정이 아님');
}

// 2) I1: 답한 뒤 다시 듣기 → 끝나기 전에 다음 문제 → 2번 문제 음이 새로 예약되고, 늦게 끝난 이전 소리가 보기를 열지 않음
{
  const { dom, audio, app } = setup();
  dom.parts['.try-play'].click(); endLatest(audio);
  dom.opts[0].click();                       // 1번 답
  ok(!dom.parts['.try-next'].hidden, '답한 뒤 다음 문제 버튼이 없음');
  ok(dom.doc.activeElement === dom.parts['.try-next'], '답한 뒤 포커스가 다음 문제로 가지 않음');
  dom.parts['.try-play'].click();            // 다시 듣기
  const staleEnd = lastOsc(audio).onended;
  const before = audio.made[0].oscs.length;
  dom.parts['.try-next'].click();            // 다시 듣기가 끝나기 전에 다음
  ok(audio.made[0].oscs.length > before, '다음 문제 음이 예약되지 않음 (이전 재생에 막힘)');
  ok(dom.doc.activeElement === dom.parts['.try-play'], '다음 문제 뒤 포커스가 듣기 버튼이 아님');
  staleEnd && staleEnd();                    // 이전 소리가 늦게 끝남
  ok(enabledCount(dom) === 0, '이전 문제의 소리가 끝나며 2번 보기를 열어 버림');
  endLatest(audio);
  ok(enabledCount(dom) === 3, '2번 소리가 끝났는데 보기가 안 열림');
}

// 3) 끝까지: 결과에 포커스, 0점이면 다독이는 문장, 다시 하기는 듣기 버튼으로 포커스
{
  const { dom, audio, timers, app } = setup();
  for (let i = 0; i < 3; i++) {
    if (i === 0) dom.parts['.try-play'].click(); else dom.parts['.try-next'].click();
    endLatest(audio);
    const ans = app.round()[i].answer;
    dom.opts.find(b => b.getAttribute('data-iv') !== ans).click();   // 일부러 모두 틀림
  }
  timers.flush();
  ok(!dom.parts['.try-done'].hidden, '결과가 안 보임');
  ok(dom.parts['.try-done-text'].textContent === '아직 맞힌 문제가 없어요.', '0점 문장이 아님: ' + dom.parts['.try-done-text'].textContent);
  ok(dom.doc.activeElement === dom.parts['.try-done-text'], '결과로 포커스가 가지 않음');
  dom.parts['.try-retry'].click();
  ok(dom.parts['.try-done'].hidden, '다시 하기 뒤 결과가 남음');
  ok(dom.doc.activeElement === dom.parts['.try-play'], '다시 하기 뒤 포커스가 듣기 버튼이 아님');
}

// 4) M1: Web Audio 가 없으면 체험을 열지 않는다 (안내 문구가 보이게)
{
  const { dom } = setup({ AudioContext: undefined });
  ok(!dom.sec.classList.contains('try-ready'), 'Web Audio 가 없는데 try-ready');
}

// 5) C1: iPhone 무음 모드 — audioSession 이 있으면 playback 으로, 없으면 무음 <audio> 로 미디어 채널을 연다
{
  const nav = { userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)', maxTouchPoints: 5, audioSession: { type: 'auto' } };
  const { dom } = setup({ navigator: nav });
  dom.parts['.try-play'].click();
  ok(nav.audioSession.type === 'playback', 'audioSession.type 이 playback 이 아님');
}
{
  let played = 0;
  const doc = { createElement: (t) => ({ tag: t, setAttribute() {}, play() { played++; return Promise.resolve(); } }) };
  const nav = { userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)', maxTouchPoints: 5 };
  const { dom } = setup({ navigator: nav, document: Object.assign(doc, { activeElement: null }) });
  dom.parts['.try-play'].click();
  ok(played === 1, '구형 iOS 에서 무음 <audio> 로 미디어 채널을 열지 않음');
}

// 6) 마스코트 없는 앱(Absolute Ear): 무대가 건반이다 — 울리는 두 음의 건반이 그때 켜지고, 답하면 두 음이 남고, 다음 문제에서 지워진다
{
  const dom = makeDom(); const audio = makeAudio(); const timers = makeTimers();
  delete dom.parts['.try-stage img'];
  dom.sec.dataset = Object.assign({}, dom.sec.dataset, { frameIdle: undefined, frameListen: undefined, frameYes: undefined, frameNo: undefined });
  const keyEls = {};
  for (let m = 55; m <= 74; m++) keyEls[m] = { m, classList: classList() };
  const keys = {
    querySelector: (sel) => { const g = /data-m="(\d+)"/.exec(sel); return g ? keyEls[+g[1]] || null : null; },
    querySelectorAll: (sel) => (sel === '.key' ? Object.values(keyEls) : []),
  };
  dom.parts['.try-keys'] = keys;
  const env = { AudioContext: audio.Ctx, setTimeout: timers.setTimeout, clearTimeout: timers.clearTimeout, random: rand,
    navigator: { userAgent: 'Mozilla/5.0 (Macintosh)', maxTouchPoints: 0 }, document: dom.doc };
  const app = T.mount(dom.sec, env);
  ok(app, '건반 무대에서 mount 실패(그림 무대가 없어도 동작해야 함)');
  const q = app.round()[0];
  const on = () => Object.values(keyEls).filter(k => k.classList.contains('on')).map(k => k.m).sort((a, b) => a - b);
  const held = () => Object.values(keyEls).filter(k => k.classList.contains('held')).map(k => k.m).sort((a, b) => a - b);
  dom.parts['.try-play'].click();
  ok(on().length === 0, '소리가 나기 전에 건반이 켜짐');
  timers.flush();                              // 켜기·끄기 예약이 모두 지나감
  ok(on().length === 0, '소리가 끝났는데 건반이 켜진 채 남음');
  endLatest(audio);
  dom.opts.find(b => b.getAttribute('data-iv') === q.answer).click();
  ok(JSON.stringify(held()) === JSON.stringify([q.root, q.top].sort((a, b) => a - b)), '답한 뒤 문제의 두 건반이 남지 않음: ' + held());
  dom.parts['.try-next'].click();
  ok(held().length === 0, '다음 문제에서 이전 건반이 지워지지 않음');
  // 켜기 예약이 실제로 그 음을 켜는지: 켜기만 먼저 실행
  const calls = [];
  const env2 = Object.assign({}, env, { setTimeout: (fn, ms) => { calls.push({ fn, ms }); return calls.length; } });
  const dom2 = makeDom(); delete dom2.parts['.try-stage img']; dom2.parts['.try-keys'] = keys;
  Object.values(keyEls).forEach(k => k.classList.remove('on', 'held'));
  const app2 = T.mount(dom2.sec, env2);
  const q2 = app2.round()[0];
  dom2.parts['.try-play'].click();
  calls.filter(c => c.ms === 50 || c.ms === 850).forEach(c => c.fn());
  ok(JSON.stringify(on()) === JSON.stringify([q2.root, q2.top].sort((a, b) => a - b)), '울리는 두 음의 건반이 켜지지 않음: ' + on());
}
process.exit(bad ? 1 : 0);
