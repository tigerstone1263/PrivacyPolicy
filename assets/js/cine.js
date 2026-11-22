// 첫 화면 스크롤 연출 (MotionSites sticky cinematic stage). 넓은 화면·마우스·동작 줄이기 아님일 때만 켠다.
// 스크롤 px → 장면 값(frame)은 순수 함수, 화면은 CSS 변수만 바꾼다. 꺼지면 정적인 첫 화면 그대로.
(function (root) {
  var RUNWAY = 1000;   // 고정된 무대 위에서 스크롤하는 거리(px)

  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function smooth(a, b, s) { var t = clamp01((s - a) / (b - a)); return t * t * (3 - 2 * t); }
  function mix(x, y, t) { return x + (y - x) * t; }
  function r3(x) { return Math.round(x * 1000) / 1000; }

  // 장면 대본: 0→420 문구가 빠지고 워드마크가 떠오른다 · 120→760 폰이 서며 다가오고 소리가 걸어 나온다 · 640→1000 자막
  function frame(s) {
    s = s < 0 ? 0 : s > RUNWAY ? RUNWAY : s;
    var out = smooth(0, 420, s), cam = smooth(120, 760, s), cap = smooth(640, 1000, s);
    return {
      copyO: r3(1 - out), copyY: r3(-90 * out),
      wordY: r3(-14 * out), wordS: r3(mix(1, 1.14, out)), wordO: r3(mix(0.55, 1, out)),
      cam: r3(cam), frontRot: r3(mix(-4, 0, cam)), frontS: r3(mix(1, 1.12, cam)), frontX: r3(mix(0, -34, cam)),
      backRot: r3(mix(6, 13, cam)), backX: r3(mix(0, 70, cam)), backY: r3(mix(0, 26, cam)),
      soriX: r3(mix(0, 64, cam)), soriS: r3(mix(1, 1.16, cam)),
      capO: r3(cap), capY: r3(mix(24, 0, cap))
    };
  }

  // 첫 화면이 좌우 배치되는 폭(1100px)부터, 마우스가 있고 동작 줄이기가 아닐 때만
  function shouldEnable(env) { return env.width >= 1100 && env.hover && !env.reduced; }

  root.Cine = { RUNWAY: RUNWAY, frame: frame, shouldEnable: shouldEnable };
  if (typeof document === 'undefined' || !document.getElementById) return;

  var hero = document.getElementById('hero');
  var stage = hero && hero.querySelector('.hero-stage');
  if (!stage) return;
  var mm = function (q) { return root.matchMedia ? root.matchMedia(q).matches : false; };
  var html = document.documentElement;
  var cur = 0, target = 0, raf = 0, on = false;

  function apply(s) {
    var f = frame(s);
    stage.style.setProperty('--copy-o', f.copyO); stage.style.setProperty('--copy-y', f.copyY + 'px');
    stage.style.setProperty('--word-y', f.wordY + 'vh'); stage.style.setProperty('--word-s', f.wordS); stage.style.setProperty('--word-o', f.wordO);
    stage.style.setProperty('--cam', f.cam); stage.style.setProperty('--front-r', f.frontRot + 'deg'); stage.style.setProperty('--front-s', f.frontS); stage.style.setProperty('--front-x', f.frontX + 'px');
    stage.style.setProperty('--back-r', f.backRot + 'deg'); stage.style.setProperty('--back-x', f.backX + 'px'); stage.style.setProperty('--back-y', f.backY + 'px');
    stage.style.setProperty('--sori-x', f.soriX + 'px'); stage.style.setProperty('--sori-s', f.soriS);
    stage.style.setProperty('--cap-o', f.capO); stage.style.setProperty('--cap-y', f.capY + 'px');
  }
  function measure() { var r = hero.getBoundingClientRect(); target = Math.max(0, Math.min(RUNWAY, -r.top)); }
  // 부드럽게 따라가기(lerp .14), 거의 닿으면 멈춘다
  function tick() {
    cur += (target - cur) * 0.14;
    if (Math.abs(target - cur) < 0.5) cur = target;
    apply(cur);
    raf = cur === target ? 0 : requestAnimationFrame(tick);
  }
  function onScroll() { measure(); if (!raf) raf = requestAnimationFrame(tick); }
  function setup() {
    var want = shouldEnable({ width: root.innerWidth, hover: mm('(hover: hover)'), reduced: mm('(prefers-reduced-motion: reduce)') });
    if (want === on) return;
    on = want;
    html.classList.toggle('cine-on', on);
    if (on) { root.addEventListener('scroll', onScroll, { passive: true }); measure(); cur = target; apply(cur); }
    else { root.removeEventListener('scroll', onScroll); apply(0); }
  }
  root.addEventListener('resize', setup);
  setup();
})(typeof window !== 'undefined' ? window : this);
