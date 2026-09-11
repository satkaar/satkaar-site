// Chiffres clés : ils défilent de 0 à leur valeur quand ils entrent dans l'écran.
// Sans JavaScript, ou si le visiteur limite les animations, la valeur finale reste affichée.
(function () {
  var compteurs = document.querySelectorAll("[data-compteur]");
  if (!compteurs.length || !("IntersectionObserver" in window)) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var DUREE = 1400;

  function animer(element) {
    var cible = parseInt(element.dataset.compteur, 10);
    var debut = null;
    element.textContent = "0";

    function pas(instant) {
      if (debut === null) debut = instant;
      var avancement = Math.min((instant - debut) / DUREE, 1);
      var adouci = 1 - Math.pow(1 - avancement, 3);
      element.textContent = String(Math.round(cible * adouci));
      if (avancement < 1) window.requestAnimationFrame(pas);
    }

    window.requestAnimationFrame(pas);
    // Filet de sécurité : si les images d'animation sont suspendues, la valeur finale s'affiche quand même.
    window.setTimeout(function () {
      element.textContent = String(cible);
    }, DUREE + 300);
  }

  var observateur = new IntersectionObserver(function (entrees) {
    entrees.forEach(function (entree) {
      if (!entree.isIntersecting) return;
      observateur.unobserve(entree.target);
      animer(entree.target);
    });
  }, { threshold: 0.6 });

  // La valeur finale reste affichée jusqu'au départ de l'animation : si l'observation
  // n'a jamais lieu, le visiteur voit le bon chiffre, jamais un zéro.
  compteurs.forEach(function (element) {
    observateur.observe(element);
  });
})();
