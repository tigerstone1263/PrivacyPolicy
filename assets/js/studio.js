// tigerstone 루트 페이지 연출.
// 1) 스크롤 무대: 활주로 진행률 p(0~1) → 장면 값(frame)은 순수 함수. 화면은 CSS 변수(--split, --rise)와 data-scene 만 바꾼다.
// 2) 소리: 앱 Rive 동작을 렌더한 투명 영상. 평소엔 idle 반복, 장면이 바뀌면 한 번 반응한 뒤 idle 로 돌아온다.
//    동작 줄이기·재생 실패 때만 정지 그림(sori-still)이 남는다.
(function (root) {
  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function smooth(a, b, x) { var t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
  function r3(x) { return Math.round(x * 1000) / 1000; }

  // 장면 대본: 0→.16 글자가 tiger | stone 으로 갈라짐 · .06→.26 폰이 올라옴 · 장면 1(.28) 2(.52) 3(.76)
  var SCENES = [0.28, 0.52, 0.76];
  function frame(p) {
    p = clamp01(p);
    var scene = 0;
    for (var i = 0; i < SCENES.length; i++) if (p >= SCENES[i]) scene = i + 1;
    return { split: r3(smooth(0, 0.16, p)), rise: r3(smooth(0.06, 0.26, p)), scene: scene };
  }
  // 장면에 들어갈 때 소리가 하는 반응 (장면 2는 반응 없이 idle)
  var REACT = { 1: 'listen', 3: 'celebrate' };

  // 투명 영상 형식: WebKit(사파리·iOS 의 모든 브라우저)은 HEVC 알파(.mov), 나머지는 VP9 알파(.webm)
  function videoExt(env) {
    if (env.ios) return 'mov';
    var ua = env.ua || '';
    return /Safari\//.test(ua) && !/Chrome|Chromium|CriOS|FxiOS|Edg|OPR|Android/.test(ua) ? 'mov' : 'webm';
  }
  function shouldEnable(env) { return !env.reduced; }

  root.Studio = { frame: frame, SCENES: SCENES, REACT: REACT, videoExt: videoExt, shouldEnable: shouldEnable };
  if (typeof document === 'undefined' || !document.getElementById) return;

  var html = document.documentElement;
  var reduced = root.matchMedia ? root.matchMedia('(prefers-reduced-motion: reduce)').matches : false;
  if (!shouldEnable({ reduced: reduced })) return;
  var ext = videoExt({ ios: html.classList.contains('os-ios'), ua: navigator.userAgent });
  var MEDIA = '/assets/media/sori-';

  // ---------- 소리 재생기 ----------
  function Sori(box) {
    this.box = box;
    this.idle = this.make(true);
    this.act = this.make(false);
    this.started = false;
    this.wanted = null;
    var self = this;
    this.act.addEventListener('playing', function () { self.show(self.act); });
    this.act.addEventListener('ended', function () { self.backToIdle(); });
    this.idle.addEventListener('playing', function () {
      if (self.act.ended || self.act.paused) self.show(self.idle);
    });
  }
  Sori.prototype.make = function (loop) {
    var v = document.createElement('video');
    v.className = 'sori-vid';
    v.muted = true; v.defaultMuted = true; v.playsInline = true; v.loop = loop; v.preload = 'none';
    v.setAttribute('muted', ''); v.setAttribute('playsinline', ''); v.setAttribute('aria-hidden', 'true');
    this.box.appendChild(v);
    return v;
  };
  Sori.prototype.show = function (v) {
    this.box.classList.add('sori-live');
    this.idle.classList.toggle('on', v === this.idle);
    this.act.classList.toggle('on', v === this.act);
    if (v === this.act) this.idle.pause();
  };
  Sori.prototype.play = function (v) {
    var box = this.box;
    var pr = v.play();
    // 저전력 모드 등으로 자동 재생이 막히면 정지 그림을 그대로 둔다
    if (pr && pr.catch) pr.catch(function () { if (!box.querySelector('.sori-vid.on')) box.classList.remove('sori-live'); });
  };
  Sori.prototype.start = function () {
    if (this.started) return;
    this.started = true;
    this.idle.src = MEDIA + 'idle.' + ext;
    this.play(this.idle);
  };
  Sori.prototype.preload = function (names) {
    for (var i = 0; i < names.length; i++) {
      var l = document.createElement('link');
      l.rel = 'prefetch'; l.href = MEDIA + names[i] + '.' + ext;
      document.head.appendChild(l);
    }
  };
  Sori.prototype.react = function (name) {
    this.start();
    var src = MEDIA + name + '.' + ext;
    if (this.act.getAttribute('src') !== src) this.act.src = src;
    else this.act.currentTime = 0;
    this.play(this.act);
  };
  // 반응의 마지막 자세 = idle 첫 자세. idle 을 처음부터 다시 틀고, 재생이 시작되면(playing) 바꿔 낀다
  Sori.prototype.backToIdle = function () {
    this.idle.currentTime = 0;
    this.play(this.idle);
  };
  Sori.prototype.pause = function () { this.idle.pause(); this.act.pause(); };
  Sori.prototype.resume = function () {
    if (!this.started) return;
    if (this.act.classList.contains('on') && !this.act.ended) this.play(this.act);
    else this.play(this.idle);
  };

  function whenVisible(el, onIn, onOut, threshold) {
    if (!('IntersectionObserver' in root)) { onIn(); return; }
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) onIn(); else if (onOut) onOut(); });
    }, { threshold: threshold || 0 }).observe(el);
  }

  // ---------- 스크롤 무대 ----------
  var stage = document.getElementById('stage');
  var pin = stage && stage.querySelector('.stage-pin');
  if (stage && pin) {
    html.classList.add('cine-on');
    var stageSori = new Sori(stage.querySelector('[data-sori="stage"]'));
    var last = -1, ticking = false, onScreen = true;
    var update = function () {
      ticking = false;
      var r = stage.getBoundingClientRect();
      var run = Math.max(1, stage.offsetHeight - innerHeight);
      var f = frame(-r.top / run);
      pin.style.setProperty('--split', f.split);
      pin.style.setProperty('--rise', f.rise);
      if (f.rise > 0.05 && !stageSori.started) {
        stageSori.start();
        stageSori.preload(['listen', 'celebrate']);
      }
      if (f.scene !== last) {
        stage.setAttribute('data-scene', f.scene);
        if (last !== -1 && f.scene > 0 && REACT[f.scene] && onScreen) stageSori.react(REACT[f.scene]);
        last = f.scene;
      }
    };
    addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    addEventListener('resize', update);
    update();
    whenVisible(stage, function () { onScreen = true; stageSori.resume(); }, function () { onScreen = false; stageSori.pause(); });
  }

  // ---------- 앱 카드의 소리: 보이면 손을 흔들고 idle ----------
  var cardBox = document.querySelector('[data-sori="card"]');
  if (cardBox) {
    var cardSori = new Sori(cardBox), waved = 0;
    whenVisible(cardBox.parentNode, function () {
      var now = Date.now();
      if (now - waved > 8000) { waved = now; cardSori.react('wave'); }
      else cardSori.resume();
    }, function () { cardSori.pause(); }, 0.4);
  }
})(typeof window !== 'undefined' ? window : globalThis);
