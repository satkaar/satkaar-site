// Messagerie de l'équipe : relève en arrière-plan, hauteur du cadre de lecture, préréglages
// d'hébergeur, signature qui suit la boîte choisie et boutons « occupés » pendant l'envoi.
(function () {
  // --- Relève ------------------------------------------------------------------
  var releve = document.querySelector("[data-releve]");
  if (releve) {
    var bouton = releve.querySelector("button");
    var libelle = releve.querySelector("[data-libelle]");
    var etat = releve.querySelector("[data-etat]");

    var occupe = function () {
      bouton.disabled = true;
      bouton.classList.add("courriel__bouton--occupe");
      libelle.textContent = "Relève…";
    };

    releve.addEventListener("submit", occupe);

    // Si la dernière relève date de plus de 5 minutes, on relève sans bloquer l'affichage.
    if (releve.hasAttribute("data-releve-auto") && window.fetch) {
      occupe();
      fetch(releve.action, {
        method: "POST",
        headers: { "X-CSRFToken": releve.querySelector("[name=csrfmiddlewaretoken]").value, "X-Requested-With": "fetch" },
        credentials: "same-origin"
      })
        .then(function (reponse) { return reponse.json(); })
        .then(function (resultat) {
          if (resultat.nouveaux > 0) {
            location.reload();
            return;
          }
          etat.textContent = resultat.erreurs.length ? resultat.erreurs.join(" ") : "À jour";
          etat.classList.toggle("courriel__etat--erreur", resultat.erreurs.length > 0);
        })
        .catch(function () { etat.textContent = "Relève impossible pour le moment."; })
        .then(function () {
          bouton.disabled = false;
          bouton.classList.remove("courriel__bouton--occupe");
          libelle.textContent = "Relever";
        });
    }
  }

  // --- Cadre de lecture : il prend la hauteur du message ------------------------
  var cadre = document.querySelector("[data-cadre]");
  if (cadre) {
    var ajuster = function () {
      try {
        var doc = cadre.contentDocument;
        cadre.style.height = Math.max(doc.documentElement.scrollHeight, doc.body ? doc.body.scrollHeight : 0) + 24 + "px";
      } catch (e) { /* cadre inaccessible : on garde la hauteur par défaut */ }
    };
    cadre.addEventListener("load", ajuster);
    window.addEventListener("resize", ajuster);
    if (cadre.contentDocument && cadre.contentDocument.readyState === "complete") ajuster();
  }

  // --- Préréglages d'hébergeur ---------------------------------------------------
  var fournisseur = document.querySelector("[data-fournisseur]");
  if (fournisseur) {
    var reglages = JSON.parse(document.getElementById("fournisseurs").textContent);
    fournisseur.addEventListener("change", function () {
      var choix = reglages[fournisseur.value];
      if (!choix) return;
      ["imap_hote", "imap_port", "smtp_hote", "smtp_port", "smtp_securite"].forEach(function (nom) {
        var champ = document.getElementById("id_" + nom);
        if (champ) champ.value = choix[nom];
      });
    });
    var adresse = document.getElementById("id_adresse");
    var identifiant = document.getElementById("id_identifiant");
    if (adresse && identifiant) {
      adresse.addEventListener("input", function () {
        if (!identifiant.dataset.touche) identifiant.value = adresse.value;
      });
      identifiant.addEventListener("input", function () { identifiant.dataset.touche = "1"; });
    }
  }

  // --- Signature qui suit la boîte d'envoi ---------------------------------------
  var boite = document.getElementById("id_compte");
  var texte = document.getElementById("id_texte");
  var signaturesJson = document.getElementById("signatures");
  if (boite && texte && signaturesJson) {
    var signatures = JSON.parse(signaturesJson.textContent);
    var bloc = function (cle) { return signatures[cle] ? "-- \n" + signatures[cle] : ""; };
    var precedente = boite.value;
    boite.addEventListener("change", function () {
      var ancien = bloc(precedente);
      var nouveau = bloc(boite.value);
      if (ancien && texte.value.indexOf(ancien) !== -1) texte.value = texte.value.replace(ancien, nouveau);
      else if (nouveau && texte.value.indexOf(nouveau) === -1) texte.value = texte.value.replace(/^\s*/, "\n\n" + nouveau + "\n\n");
      precedente = boite.value;
    });
    // Réponse ou transfert : curseur au début, au-dessus de la signature et du message cité.
    var mode = document.querySelector("input[name=mode]");
    if (mode && mode.value === "transferer" && !document.querySelector(".erreur")) {
      document.getElementById("id_a").focus();
    } else if (mode && !document.querySelector(".erreur")) {
      texte.focus();
      texte.setSelectionRange(0, 0);
      texte.scrollTop = 0;
    }
  }

  // --- Bouton occupé pendant l'envoi ----------------------------------------------
  document.querySelectorAll("[data-envoyer]").forEach(function (bouton) {
    bouton.form.addEventListener("submit", function () {
      if (bouton.dataset.occupe) return;
      bouton.dataset.occupe = "1";
      setTimeout(function () { bouton.disabled = true; }, 0);
      var libelle = bouton.querySelector("[data-libelle]");
      if (libelle) libelle.textContent = libelle.textContent === "Envoyer" ? "Envoi…" : "Vérification…";
    });
  });
})();
