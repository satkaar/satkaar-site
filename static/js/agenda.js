// Agenda : heures masquées pour une journée entière, fin qui suit le début, et la grille de la
// semaine qui s'ouvre sur les heures de bureau.
(function () {
  var journee = document.getElementById("id_journee_entiere");
  if (journee) {
    var basculer = function () {
      document.querySelectorAll("[data-heures]").forEach(function (bloc) { bloc.hidden = journee.checked; });
    };
    journee.addEventListener("change", basculer);
    basculer();
  }

  var debut = document.getElementById("id_heure_debut");
  var fin = document.getElementById("id_heure_fin");
  if (debut && fin) {
    debut.addEventListener("change", function () {
      if (!debut.value || (fin.value && fin.value > debut.value)) return;
      var parties = debut.value.split(":");
      var heure = Math.min(23, parseInt(parties[0], 10) + 1);
      fin.value = (heure < 10 ? "0" : "") + heure + ":" + parties[1];
    });
  }

  var dateDebut = document.getElementById("id_date_debut");
  var dateFin = document.getElementById("id_date_fin");
  if (dateDebut && dateFin) {
    var borner = function () { dateFin.min = dateDebut.value; };
    dateDebut.addEventListener("change", function () {
      borner();
      if (dateFin.value && dateFin.value < dateDebut.value) dateFin.value = "";
    });
    borner();
  }
})();
