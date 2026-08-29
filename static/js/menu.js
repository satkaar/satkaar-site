// Bascule du menu sur petit écran. Le site reste utilisable sans JavaScript :
// sans lui, la navigation s'affiche en pile sous l'en-tête.
(function () {
  var bascule = document.querySelector(".bascule-menu");
  var nav = document.getElementById("navigation-principale");
  if (!bascule || !nav) return;

  bascule.addEventListener("click", function () {
    var ouvert = nav.getAttribute("data-ouvert") === "true";
    nav.setAttribute("data-ouvert", String(!ouvert));
    bascule.setAttribute("aria-expanded", String(!ouvert));
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && nav.getAttribute("data-ouvert") === "true") {
      nav.setAttribute("data-ouvert", "false");
      bascule.setAttribute("aria-expanded", "false");
      bascule.focus();
    }
  });
})();
