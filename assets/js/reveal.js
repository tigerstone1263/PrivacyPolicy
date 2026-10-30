// 스크롤 등장 페이드. <html class="js"> 일 때만 .reveal 을 숨겨 두므로 JS 가 없으면 처음부터 보인다.
// 소리 동작 영상(.pose-video)은 화면에 보일 때만 재생한다 (동작 줄이기 설정이면 정지 프레임만).
(function () {
  var items = document.querySelectorAll('.reveal');
  var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (still || !('IntersectionObserver' in window)) {
    for (var i = 0; i < items.length; i++) items[i].classList.add('in');
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  items.forEach(function (el) { io.observe(el); });

  var videos = document.querySelectorAll('.pose-video');
  var vio = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { var p = e.target.play(); if (p && p.catch) p.catch(function () {}); }
      else e.target.pause();
    });
  }, { threshold: 0.25 });
  videos.forEach(function (v) { vio.observe(v); });
})();
