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

// Heures déjà prises (agenda de l'équipe, autres demandes) : grisées pour le jour choisi.
(function () {
  var source = document.getElementById("creneaux-pris");
  if (!source) return;
  var pris = JSON.parse(source.textContent);
  var jours = document.querySelectorAll('input[name="rappel_jour"]');
  var heures = document.querySelectorAll('.puce--heure input[name="rappel_heure"]');
  var indifferente = document.querySelector('input[name="rappel_heure"][value=""]');

  function appliquer() {
    var jour = document.querySelector('input[name="rappel_jour"]:checked');
    var occupees = (jour && pris[jour.value]) || [];
    heures.forEach(function (radio) {
      var prise = occupees.indexOf(radio.value) !== -1;
      radio.disabled = prise;
      radio.closest(".puce").title = prise ? "Déjà réservé" : "";
      radio.parentNode.querySelector("[data-etat-creneau]").textContent = prise ? ", déjà réservé" : "";
      if (prise && radio.checked) {
        radio.checked = false;
        if (indifferente) indifferente.checked = true;
      }
    });
  }

  jours.forEach(function (radio) { radio.addEventListener("change", appliquer); });
  appliquer();
})();
