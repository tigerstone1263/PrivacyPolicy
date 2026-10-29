// 언어 선택: 고른 언어는 기억하고, 루트(/)에 처음 온 방문자만 브라우저 언어로 보낸다.
// 언어 링크는 /?lang=ko 처럼 고른 언어를 URL 에 싣는다 — 저장소가 막혀도, 새 탭으로 열어도 지켜진다.
(function () {
  var KEY = 'ae-lang';
  var PATHS = { ko: '/', en: '/en/', zh: '/zh/' };

  function saved() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function save(lang) {
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }

  function detect() {
    var list = navigator.languages || [navigator.language || ''];
    for (var i = 0; i < list.length; i++) {
      var l = (list[i] || '').toLowerCase();
      if (l.indexOf('ko') === 0) return 'ko';
      if (l.indexOf('zh') === 0) return 'zh';
      if (l.indexOf('en') === 0) return 'en';
    }
    return 'en';
  }

  if (location.pathname === '/') {
    var m = /[?&]lang=(ko|en|zh)\b/.exec(location.search);
    var target;
    if (m) {
      target = m[1];
      save(target);
    } else {
      target = saved();
      if (!PATHS[target]) target = detect();
    }
    if (target !== 'ko') {
      var rest = location.search.replace(/([?&])lang=(ko|en|zh)(&|$)/, '$1').replace(/[?&]$/, '');
      location.replace(PATHS[target] + rest + location.hash);
    }
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-lang]');
    if (a) save(a.getAttribute('data-lang'));
  });
})();
