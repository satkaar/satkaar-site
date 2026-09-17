// Tableau de prospection : changer l'étape dans la liste envoie le formulaire de la ligne.
// Sans JavaScript, le bouton « OK » de chaque ligne fait le même travail.
(function () {
  var choix = document.querySelectorAll("[data-auto-envoi]");
  if (!choix.length) return;
  document.querySelectorAll("[data-sans-js]").forEach(function (bouton) { bouton.hidden = true; });
  var envoi = false;
  choix.forEach(function (select) {
    select.addEventListener("change", function () {
      if (envoi) return;  // une seule ligne part à la fois
      envoi = true;
      select.form.submit();
      // Après l'envoi seulement : un champ désactivé ne serait pas transmis.
      window.setTimeout(function () { select.setAttribute("aria-busy", "true"); }, 0);
    });
  });
})();
