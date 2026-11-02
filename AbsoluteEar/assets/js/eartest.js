// 청음 맛보기: 두 음을 차례로 듣고 음정(장3도·완전4도·완전5도)을 고른다. 앱의 음정 문제를 짧게 체험하는 용도.
// 문제 생성·채점은 순수 함수, 화면 연결은 mount(sec, env) — 둘 다 _dev/test_eartest*.js 가 node 로 확인한다.
(function (root) {
  var INTERVALS = [{ key: 'maj3', semi: 4 }, { key: 'p4', semi: 5 }, { key: 'p5', semi: 7 }];
  var ROUNDS = 3;

  function midiToHz(m) { return 440 * Math.pow(2, (m - 69) / 12); }

  // 문제마다 따로 뽑는다(소거법으로 풀리지 않게). 바로 앞 문제와 같은 음정만 피한다. 근음은 G3(55)~G4(67)
  function makeRound(rand) {
    var out = [], prev = null;
    for (var i = 0; i < ROUNDS; i++) {
      var pool = INTERVALS.filter(function (iv) { return iv.key !== prev; });
      var iv = pool[Math.floor(rand() * pool.length)];
      var r = 55 + Math.floor(rand() * 13);
      out.push({ root: r, top: r + iv.semi, answer: iv.key });
      prev = iv.key;
    }
    return out;
  }

  function grade(q, key) { return q.answer === key; }

  // 무음(0.1초) WAV — 구형 iOS 에서 <audio> 를 한 번 재생해 무음 스위치와 상관없는 미디어 채널을 연다
  var SILENT_WAV = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQQAAACAgICA';

  function mount(sec, env) {
    var AC = env.AudioContext;
    if (!AC) return null;              // Web Audio 가 없으면 try-ready 를 달지 않는다 → 안내 문구가 보인다
    sec.classList.add('try-ready');

    var stage = sec.querySelector('.try-stage img');
    var progress = sec.querySelector('.try-progress');
    var playBtn = sec.querySelector('.try-play');
    var playIco = sec.querySelector('.try-play .ico');
    var playLbl = sec.querySelector('.try-play .lbl');
    var options = Array.prototype.slice.call(sec.querySelectorAll('button[data-iv]'));
    var feedback = sec.querySelector('.try-feedback');
    var nextBtn = sec.querySelector('.try-next');
    var done = sec.querySelector('.try-done');
    var doneText = sec.querySelector('.try-done-text');
    var retryBtn = sec.querySelector('.try-retry');
    var more = sec.querySelector('.try-more');
    var moreDefault = more.textContent;
    var d = sec.dataset;
    var nav = env.navigator || {};
    var ua = nav.userAgent || '';
    var ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && nav.maxTouchPoints > 1);

    var audio = null, unlocked = false, voice = null, token = 0, finishTimer = null;
    var round, idx, score, answered;

    function frame(name) { stage.src = d['frame' + name]; }
    function fill(tpl, k, v) { return tpl.replace('{' + k + '}', v); }
    function label(replay) { playIco.textContent = replay ? '↻' : '▶'; playLbl.textContent = replay ? d.replay : d.play; }

    // iPhone 은 Web Audio 를 벨소리 채널로 내서 무음 모드면 안 들린다 — 미디어(playback) 채널로 바꾼다
    function unlockSilentSwitch() {
      if (unlocked) return;
      unlocked = true;
      if (nav.audioSession) { try { nav.audioSession.type = 'playback'; } catch (e) {} return; }
      if (ios && env.document && env.document.createElement) {
        var el = env.document.createElement('audio');
        el.setAttribute('playsinline', '');
        el.src = SILENT_WAV;
        var p = el.play(); if (p && p.catch) p.catch(function () {});
      }
    }

    // 한 음: 기본음은 길게, 높은 배음일수록 빨리 사라지게 (피아노에 가까운 울림). 끝나는 시각을 돌려준다
    function tone(out, hz, t0, dur) {
      var env1 = audio.createGain();
      env1.gain.setValueAtTime(0.0001, t0);
      env1.gain.exponentialRampToValueAtTime(0.26, t0 + 0.012);
      env1.gain.setTargetAtTime(0.0001, t0 + 0.012, dur / 3.5);
      env1.connect(out);
      var end = t0 + dur + 0.25, last = null;
      [[1, 1], [2, 0.42], [3, 0.2], [4, 0.1], [5, 0.05]].forEach(function (p) {
        var o = audio.createOscillator(), g = audio.createGain();
        o.type = 'sine'; o.frequency.value = hz * p[0];
        g.gain.setValueAtTime(p[1], t0);
        if (p[0] > 1) g.gain.setTargetAtTime(0.0001, t0, dur / (2 * p[0]));
        o.connect(g); g.connect(env1); o.start(t0); o.stop(end);
        last = o;
      });
      return last;
    }

    function stopVoice() {
      if (!voice) return;
      try { voice.out.disconnect(); } catch (e) {}
      voice = null;
    }

    function play() {
      try {
        unlockSilentSwitch();
        audio = audio || new AC();
        if (audio.resume) { var r = audio.resume(); if (r && r.catch) r.catch(function () {}); }
      } catch (e) { sec.classList.remove('try-ready'); return; }   // 오디오를 못 열면 안내 문구로 돌아간다
      stopVoice();
      var my = ++token, q = round[idx], t = audio.currentTime + 0.05;
      var out = audio.createGain(); out.gain.value = 1; out.connect(audio.destination);
      voice = { out: out };
      tone(out, midiToHz(q.root), t, 1.1);
      var last = tone(out, midiToHz(q.top), t + 0.8, 1.3);
      if (!answered) { frame('Listen'); options.forEach(function (b) { b.disabled = true; }); }
      label(true);
      // 이 재생의 마지막 음이 실제로 끝났을 때만 잠금을 푼다 (다음 문제로 넘어갔다면 무시)
      last.onended = function () {
        if (my !== token) return;
        stopVoice();
        if (audio.suspend) { var s = audio.suspend(); if (s && s.catch) s.catch(function () {}); }
        if (!answered) { frame('Idle'); options.forEach(function (b) { b.disabled = false; }); }
      };
    }

    function choose(btn) {
      if (answered) return;
      answered = true;
      var q = round[idx], right = grade(q, btn.getAttribute('data-iv'));
      var answerBtn = options.filter(function (b) { return b.getAttribute('data-iv') === q.answer; })[0];
      if (right) score++;
      btn.classList.add(right ? 'is-right' : 'is-wrong');
      answerBtn.classList.add('is-right');
      options.forEach(function (b) { b.disabled = true; });
      frame(right ? 'Yes' : 'No');
      feedback.textContent = right ? d.correct : fill(d.wrong, 'a', answerBtn.textContent.trim());
      if (idx < round.length - 1) { nextBtn.hidden = false; nextBtn.focus(); }
      else finishTimer = env.setTimeout(finish, 900);
    }

    function setQuestion() {
      token++;                         // 이전 문제의 재생 콜백을 무효로
      stopVoice();
      answered = false;
      progress.textContent = fill(d.q, 'n', idx + 1);
      feedback.textContent = '';
      nextBtn.hidden = true;
      options.forEach(function (b) { b.classList.remove('is-right', 'is-wrong'); b.disabled = true; });
      label(false);
      frame('Idle');
    }

    // 점수에 맞춘 한마디: 만점·0점은 따로 쓰고, 1문제 이하면 다독이는 말로 앱 안내를 바꾼다
    function finish() {
      doneText.textContent = score === round.length ? d.perfect : score === 0 ? d.zero : fill(d.result, 'k', score);
      if (score <= 1) more.textContent = d.keep;
      done.hidden = false;
      frame(score >= 2 ? 'Yes' : 'No');
      doneText.focus();
    }

    function start() {
      if (finishTimer) { env.clearTimeout(finishTimer); finishTimer = null; }
      round = makeRound(env.random || Math.random); idx = 0; score = 0;
      done.hidden = true; more.textContent = moreDefault;
      setQuestion();
    }

    playBtn.addEventListener('click', play);
    options.forEach(function (b) { b.addEventListener('click', function () { choose(b); }); });
    nextBtn.addEventListener('click', function () { idx++; setQuestion(); playBtn.focus(); play(); });
    retryBtn.addEventListener('click', function () { start(); playBtn.focus(); play(); });
    start();
    return { round: function () { return round; } };
  }

  root.EarTest = { INTERVALS: INTERVALS, ROUNDS: ROUNDS, midiToHz: midiToHz, makeRound: makeRound, grade: grade, mount: mount };

  if (typeof document === 'undefined' || !document.getElementById) return;
  var sec = document.getElementById('try');
  if (sec) mount(sec, { AudioContext: root.AudioContext || root.webkitAudioContext, setTimeout: root.setTimeout.bind(root),
    clearTimeout: root.clearTimeout.bind(root), navigator: root.navigator, document: document });
})(typeof window !== 'undefined' ? window : this);
