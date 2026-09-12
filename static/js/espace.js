// Espace : le rail ouvre le volet de la rubrique sans changer de page (comme dans le CRM),
// et le menu du compte se referme au clic en dehors ou avec la touche Échap.
(function () {
  var rubriques = document.querySelectorAll("[data-rubrique]");
  rubriques.forEach(function (rubrique) {
    rubrique.addEventListener("click", function (evenement) {
      if (window.matchMedia("(max-width: 1000px)").matches) return; // petit écran : tout est déjà visible
      evenement.preventDefault();
      rubriques.forEach(function (autre) {
        var active = autre === rubrique;
        autre.classList.toggle("app__rubrique--active", active);
        if (active) autre.setAttribute("aria-current", "true");
        else autre.removeAttribute("aria-current");
        document.getElementById(autre.getAttribute("aria-controls")).classList.toggle("app__panneau--replie", !active);
      });
      var premier = document.querySelector("#" + rubrique.getAttribute("aria-controls") + " .app__lien");
      if (premier) premier.focus();
    });
  });

  var menu = document.querySelector(".app__compte");
  if (!menu) return;

  document.addEventListener("click", function (evenement) {
    if (menu.open && !menu.contains(evenement.target)) menu.open = false;
  });

  document.addEventListener("keydown", function (evenement) {
    if (evenement.key === "Escape" && menu.open) {
      menu.open = false;
      menu.querySelector("summary").focus();
    }
  });
})();
