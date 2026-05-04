(function () {
  var nav = document.getElementById("site-navbar");
  if (!nav) return;

  function updateScrollState() {
    if (window.scrollY > 10) {
      nav.classList.add("navbar-scrolled");
    } else {
      nav.classList.remove("navbar-scrolled");
    }
  }

  window.addEventListener("scroll", updateScrollState, { passive: true });
  updateScrollState();
})();
