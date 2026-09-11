// Apparitions au défilement : les blocs montent en fondu, en cascade, quand ils entrent
// dans l'écran. Sans JavaScript, sans IntersectionObserver ou si le visiteur limite les
// animations, tout reste affiché d'emblée.
(function () {
  if (!("IntersectionObserver" in window)) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var SELECTEURS = [
    ".section h2", ".section .chapo", ".carte", ".expertise", ".etapes li", ".domaines li",
    ".labels-tuiles li", ".reference", ".fondateur", ".parcours__liste li", ".produit",
    ".cta", ".verbatim", ".photo-lieu", ".carte-saisie", ".tarif", ".carte-territoire",
    ".bento__case"
  ].join(", ");
  var DECALAGE = 70; // ms entre deux éléments voisins
  var DUREE = 900;

  function reveler(element) {
    element.classList.add("apparu");
    // Une fois arrivé, l'élément retrouve ses transitions normales (survol sans délai).
    var delai = parseInt(element.style.getPropertyValue("--delai"), 10) || 0;
    window.setTimeout(function () {
      element.classList.remove("a-apparaitre", "apparu");
      element.style.removeProperty("--delai");
    }, DUREE + delai + 100);
  }

  var observateur = new IntersectionObserver(function (entrees) {
    entrees.forEach(function (entree) {
      if (!entree.isIntersecting) return;
      observateur.unobserve(entree.target);
      reveler(entree.target);
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

  document.querySelectorAll(SELECTEURS).forEach(function (element) {
    // Un bloc déjà animé avec son parent ne s'anime pas une seconde fois.
    if (element.parentElement.closest(".a-apparaitre")) return;
    var voisins = Array.prototype.filter.call(element.parentElement.children, function (voisin) {
      return voisin.matches(SELECTEURS);
    });
    var rang = Math.min(voisins.indexOf(element), 6);
    element.style.setProperty("--delai", rang * DECALAGE + "ms");
    element.classList.add("a-apparaitre");
    observateur.observe(element);
  });
})();
