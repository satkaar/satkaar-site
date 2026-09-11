// Défilement des pastilles de jours : flèches et fondu sur les bords.
// Sans JavaScript, la rangée défile simplement au doigt ou à la molette.
(function () {
  document.querySelectorAll("[data-defilement]").forEach(function (cadre) {
    var zone = cadre.querySelector(".creneaux__defilement");
    var precedent = cadre.querySelector(".creneaux__fleche--precedent");
    var suivant = cadre.querySelector(".creneaux__fleche--suivant");

    function mettreAJour() {
      var reste = zone.scrollWidth - zone.clientWidth - zone.scrollLeft;
      var aGauche = zone.scrollLeft > 2;
      var aDroite = reste > 2;
      precedent.hidden = !aGauche;
      suivant.hidden = !aDroite;
      cadre.classList.toggle("creneaux__cadre--gauche", aGauche);
      cadre.classList.toggle("creneaux__cadre--droite", aDroite);
    }

    function defiler(sens) {
      zone.scrollBy({ left: sens * zone.clientWidth * 0.75, behavior: "smooth" });
    }

    precedent.addEventListener("click", function () { defiler(-1); });
    suivant.addEventListener("click", function () { defiler(1); });
    zone.addEventListener("scroll", mettreAJour, { passive: true });
    window.addEventListener("resize", mettreAJour);

    // Après une erreur de saisie, le jour déjà choisi reste visible.
    var coche = zone.querySelector(".puce__radio:checked");
    if (coche) {
      var puce = coche.closest(".puce");
      zone.scrollLeft = Math.max(0, puce.offsetLeft - zone.clientWidth / 2 + puce.offsetWidth / 2);
    }

    // Une pastille atteinte au clavier est ramenée dans la zone visible.
    zone.addEventListener("focusin", function (evenement) {
      var cible = evenement.target.closest(".puce");
      if (cible) cible.scrollIntoView({ block: "nearest", inline: "nearest" });
    });

    mettreAJour();
  });
})();
