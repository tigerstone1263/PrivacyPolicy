// 언어 선택.
// - 브라우저 언어만으로는 이동하지 않는다: 검색 로봇이 / 를 리디렉션으로 보면 한국어 페이지가 색인에서 빠진다.
//   대신 루트(/)에서 브라우저 언어가 한국어가 아니면 그 언어로 가는 안내 띠를 보여 준다.
// - 방문자가 직접 고른 언어(언어 링크의 ?lang=, 저장값)만 이동 근거가 된다.
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

  var suggest = null;
  if (location.pathname === '/') {
    var m = /[?&]lang=(ko|en|zh)\b/.exec(location.search);
    var chosen = m ? m[1] : saved();
    if (m) save(chosen);
    if (PATHS[chosen]) {
      if (chosen !== 'ko') {
        var rest = location.search.replace(/([?&])lang=(ko|en|zh)(&|$)/, '$1').replace(/[?&]$/, '');
        location.replace(PATHS[chosen] + rest + location.hash);
      }
    } else if (detect() !== 'ko') {
      suggest = detect();
    }
  }

  function showBanner() {
    var el = document.getElementById('lang-banner');
    if (!suggest || !el) return;
    el.setAttribute('data-suggest', suggest);
    el.hidden = false;
    var close = el.querySelector('.lang-banner-close');
    if (close) close.addEventListener('click', function () { el.hidden = true; save('ko'); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', showBanner);
  else showBanner();

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-lang]');
    if (a) save(a.getAttribute('data-lang'));
  });
})();
