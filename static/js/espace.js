// Menu du compte (espace) : se referme au clic en dehors ou avec la touche Échap.
(function () {
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
