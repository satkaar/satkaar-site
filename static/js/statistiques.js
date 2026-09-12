// Infobulles des graphiques de statistiques : au survol et au clavier (flèches ou tabulation).
// Les valeurs restent lisibles sans elles, dans les tableaux « Voir les données ».
(function () {
  function placer(infobulle, conteneur, x, y) {
    var boite = conteneur.getBoundingClientRect();
    infobulle.hidden = false;
    var gauche = Math.min(Math.max(x - boite.left + 12, 0), boite.width - infobulle.offsetWidth);
    infobulle.style.left = gauche + "px";
    infobulle.style.top = Math.max(y - boite.top - infobulle.offsetHeight - 12, 0) + "px";
  }

  function remplir(infobulle, valeur, libelle) {
    infobulle.textContent = "";
    var fort = document.createElement("strong");
    fort.textContent = valeur;
    var petit = document.createElement("span");
    petit.textContent = libelle;
    infobulle.appendChild(fort);
    infobulle.appendChild(petit);
  }

  // Courbe : un viseur vertical suit le pointeur et s'accroche au jour le plus proche.
  document.querySelectorAll('[data-graphe="courbe"]').forEach(function (conteneur) {
    var svg = conteneur.querySelector("svg");
    var points = JSON.parse(document.getElementById("points-courbe").textContent);
    var viseur = svg.querySelector(".graphe__viseur");
    var curseur = svg.querySelector(".graphe__curseur");
    var infobulle = conteneur.querySelector(".graphe__infobulle");
    var rang = points.length - 1;

    function montrer(i) {
      if (!points.length) return;
      rang = Math.max(0, Math.min(points.length - 1, i));
      var p = points[rang];
      viseur.setAttribute("x1", p.x); viseur.setAttribute("x2", p.x); viseur.hidden = false;
      curseur.setAttribute("cx", p.x); curseur.setAttribute("cy", p.y); curseur.hidden = false;
      remplir(infobulle, p.v + (p.v > 1 ? " visites" : " visite"), p.t);
      var echelle = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
      var boite = svg.getBoundingClientRect();
      placer(infobulle, conteneur, boite.left + p.x * echelle, boite.top + p.y * echelle);
    }
    function cacher() { viseur.hidden = true; curseur.hidden = true; infobulle.hidden = true; }

    svg.addEventListener("pointermove", function (e) {
      var boite = svg.getBoundingClientRect();
      var x = (e.clientX - boite.left) * svg.viewBox.baseVal.width / boite.width;
      var proche = 0;
      points.forEach(function (p, i) { if (Math.abs(p.x - x) < Math.abs(points[proche].x - x)) proche = i; });
      montrer(proche);
    });
    svg.addEventListener("pointerleave", cacher);
    svg.addEventListener("focus", function () { montrer(rang); });
    svg.addEventListener("blur", cacher);
    svg.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { montrer(rang - 1); e.preventDefault(); }
      if (e.key === "ArrowRight") { montrer(rang + 1); e.preventDefault(); }
    });
  });

  // Colonnes : chaque colonne est sa propre cible, plus large que la barre dessinée.
  document.querySelectorAll('[data-graphe="colonnes"]').forEach(function (conteneur) {
    var infobulle = conteneur.querySelector(".graphe__infobulle");
    conteneur.querySelectorAll(".colonne").forEach(function (colonne) {
      function montrer() {
        remplir(infobulle, colonne.dataset.valeur + " visite" + (colonne.dataset.valeur === "1" || colonne.dataset.valeur === "0" ? "" : "s"), colonne.dataset.libelle);
        var boite = colonne.getBoundingClientRect();
        placer(infobulle, conteneur, boite.left + boite.width / 2, boite.top + 20);
      }
      colonne.addEventListener("pointerenter", montrer);
      colonne.addEventListener("focus", montrer);
      colonne.addEventListener("pointerleave", function () { infobulle.hidden = true; });
      colonne.addEventListener("blur", function () { infobulle.hidden = true; });
    });
  });
})();
