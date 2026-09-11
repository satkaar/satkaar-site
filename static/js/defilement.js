// Bouton Pause du bandeau « Ils nous font confiance » (RGAA 13.8 : tout contenu en
// mouvement doit pouvoir être arrêté). Sans JavaScript, le survol suffit à le figer.
(function () {
  var bandeau = document.querySelector(".confiance");
  if (!bandeau) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var bouton = bandeau.querySelector(".confiance__pause");
  var libelle = bouton.querySelector("[data-libelle]");
  var defilement = bandeau.querySelector(".defilement");

  bouton.hidden = false;
  bouton.addEventListener("click", function () {
    var enPause = bouton.getAttribute("aria-pressed") !== "true";
    bouton.setAttribute("aria-pressed", String(enPause));
    libelle.textContent = enPause ? "Reprendre le défilement" : "Mettre en pause";
    defilement.classList.toggle("defilement--pause", enPause);
  });
})();
