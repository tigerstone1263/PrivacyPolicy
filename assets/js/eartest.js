// 청음 맛보기: 두 음을 차례로 듣고 음정(장3도·완전4도·완전5도)을 고른다. 앱의 음정 문제를 짧게 체험하는 용도.
// 문제 생성·채점(EarTest)은 DOM 과 분리되어 있어 _dev/test_eartest.js 가 node 로 확인한다.
(function (root) {
  var INTERVALS = [{ key: 'm3', semi: 4 }, { key: 'p4', semi: 5 }, { key: 'p5', semi: 7 }];
  var ROUNDS = 3;

  function midiToHz(m) { return 440 * Math.pow(2, (m - 69) / 12); }

  // 한 판: 세 음정을 한 번씩 섞어서, 근음은 G3(55)~G4(67)
  function makeRound(rand) {
    var order = INTERVALS.slice();
    for (var i = order.length - 1; i > 0; i--) {
      var j = Math.floor(rand() * (i + 1)); var t = order[i]; order[i] = order[j]; order[j] = t;
    }
    return order.map(function (iv) {
      var r = 55 + Math.floor(rand() * 13);
      return { root: r, top: r + iv.semi, answer: iv.key };
    });
  }

  function grade(q, key) { return q.answer === key; }

  root.EarTest = { INTERVALS: INTERVALS, ROUNDS: ROUNDS, midiToHz: midiToHz, makeRound: makeRound, grade: grade };

  if (typeof document === 'undefined' || !document.getElementById) return;
  var sec = document.getElementById('try');
  if (!sec) return;

  var stage = sec.querySelector('.try-stage img');
  var progress = sec.querySelector('.try-progress');
  var playBtn = sec.querySelector('.try-play');
  var options = Array.prototype.slice.call(sec.querySelectorAll('button[data-iv]'));
  var feedback = sec.querySelector('.try-feedback');
  var nextBtn = sec.querySelector('.try-next');
  var done = sec.querySelector('.try-done');
  var doneText = sec.querySelector('.try-done-text');
  var retryBtn = sec.querySelector('.try-retry');
  var more = sec.querySelector('.try-more');
  var moreDefault = more.textContent;
  var d = sec.dataset;

  var audio = null, round, idx, score, answered, playing = false;

  function frame(name) { stage.src = d['frame' + name]; }
  function fill(tpl, k, v) { return tpl.replace('{' + k + '}', v); }

  function tone(ctx, hz, t0, dur) {
    var out = ctx.createGain();
    out.gain.setValueAtTime(0.0001, t0);
    out.gain.exponentialRampToValueAtTime(0.3, t0 + 0.012);
    out.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    out.connect(ctx.destination);
    // 피아노에 가까운 음색: 배음을 겹치고 높은 배음일수록 빨리 사라지게
    [[1, 1], [2, 0.45], [3, 0.22], [4, 0.12], [5, 0.06]].forEach(function (p) {
      var o = ctx.createOscillator(); var g = ctx.createGain();
      o.type = 'sine'; o.frequency.value = hz * p[0];
      g.gain.setValueAtTime(p[1], t0);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur / (0.4 + 0.6 * p[0]));
      o.connect(g); g.connect(out); o.start(t0); o.stop(t0 + dur + 0.05);
    });
  }

  function play() {
    var AC = root.AudioContext || root.webkitAudioContext;
    if (!AC || playing) return;
    audio = audio || new AC();
    if (audio.resume) audio.resume();
    var q = round[idx], t = audio.currentTime + 0.05;
    tone(audio, midiToHz(q.root), t, 1.0);
    tone(audio, midiToHz(q.top), t + 0.75, 1.2);
    playing = true;
    if (!answered) frame('Listen');
    playBtn.textContent = d.replay;
    setTimeout(function () {
      playing = false;
      if (!answered) frame('Idle');
      options.forEach(function (b) { b.disabled = answered; });
    }, 1900);
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
    else setTimeout(finish, 900);
  }

  function setQuestion() {
    answered = false;
    progress.textContent = fill(d.q, 'n', idx + 1);
    feedback.textContent = '';
    nextBtn.hidden = true;
    options.forEach(function (b) { b.classList.remove('is-right', 'is-wrong'); b.disabled = true; });
    playBtn.textContent = d.play;
    frame('Idle');
  }

  function finish() {
    // 점수에 맞춘 한마디: 만점이면 칭찬 문장, 1문제 이하면 다독이는 말로 앱 안내를 바꾼다
    doneText.textContent = score === round.length ? d.perfect : fill(d.result, 'k', score);
    if (score <= 1) more.textContent = d.keep;
    done.hidden = false;
    frame(score >= 2 ? 'Yes' : 'No');
  }

  function start() {
    round = makeRound(Math.random); idx = 0; score = 0; done.hidden = true; more.textContent = moreDefault;
    setQuestion();
  }

  playBtn.addEventListener('click', play);
  options.forEach(function (b) { b.addEventListener('click', function () { choose(b); }); });
  nextBtn.addEventListener('click', function () { idx++; setQuestion(); play(); });
  retryBtn.addEventListener('click', function () { start(); play(); });
  start();
})(typeof window !== 'undefined' ? window : this);
