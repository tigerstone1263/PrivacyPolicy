// 언어 선택: 고른 언어는 기억하고, 루트(/)에 처음 온 방문자만 브라우저 언어로 보낸다.
(function () {
  var KEY = 'ae-lang';
  var PATHS = { ko: '/', en: '/en/', zh: '/zh/' };

  function saved() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
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
    var target = saved();
    if (!PATHS[target]) target = detect();
    if (target !== 'ko') location.replace(PATHS[target] + location.search + location.hash);
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-lang]');
    if (!a) return;
    try { localStorage.setItem(KEY, a.getAttribute('data-lang')); } catch (err) {}
  });
})();
