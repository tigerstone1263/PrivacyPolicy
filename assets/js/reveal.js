// 스크롤 등장 페이드. <html class="js"> 일 때만 .reveal 을 숨겨 두므로 JS 가 없으면 처음부터 보인다.
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


  // 기능 카드: 스크롤이 진행되면 아래에 깔린 카드가 살짝 작아진다 (MotionSites sticky stacking cards)
  var stack = document.querySelector('.stack');
  if (stack && !still) {
    var cards = [].slice.call(stack.querySelectorAll('.fcard'));
    var n = cards.length, ticking = false;
    var update = function () {
      ticking = false;
      var r = stack.getBoundingClientRect();
      var p = Math.min(1, Math.max(0, -r.top / Math.max(1, r.height - innerHeight)));
      cards.forEach(function (card, i) {
        var target = 1 - (n - 1 - i) * 0.035;
        var t = Math.min(1, Math.max(0, (p - i / n) / (1 - i / n)));
        card.style.transform = 'scale(' + (1 + (target - 1) * t).toFixed(4) + ')';
      });
    };
    addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    addEventListener('resize', update);
    update();
  }
})();
