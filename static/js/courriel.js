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
    var choisir = function (cle) {
      if (fournisseur.value === cle) return;
      fournisseur.value = cle;
      fournisseur.dispatchEvent(new Event("change"));
    };
    if (adresse && identifiant) {
      adresse.addEventListener("input", function () {
        if (!identifiant.dataset.touche) identifiant.value = adresse.value;
        // Une adresse Gmail remplit les serveurs de Google ; les autres gardent le réglage choisi.
        var domaine = (adresse.value.split("@")[1] || "").toLowerCase();
        if (domaine === "gmail.com" || domaine === "googlemail.com") choisir("google");
      });
      identifiant.addEventListener("input", function () { identifiant.dataset.touche = "1"; });
    }
  }

  // --- Curseur au bon endroit en réponse et en transfert --------------------------
  var texte = document.getElementById("id_texte");
  if (texte) {
    var mode = document.querySelector("input[name=mode]");
    if (mode && mode.value === "transferer" && !document.querySelector(".erreur")) {
      document.getElementById("id_a").focus();
    } else if (mode && !document.querySelector(".erreur") && !texte.hidden) {
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
      if (libelle) libelle.textContent = bouton.dataset.texteOccupe || (libelle.textContent === "Envoyer" ? "Envoi…" : "Vérification…");
    });
  });
})();

// --- Éditeur de message : mise en forme, liens et émojis ---------------------------
// Sans JavaScript, la zone de texte simple reste utilisée telle quelle : on ne l'échange
// contre l'éditeur qu'ici, une fois le script chargé.
(function () {
  var editeur = document.querySelector("[data-editeur]");
  if (!editeur) return;
  var zone = editeur.querySelector("[data-zone]");
  var texte = document.getElementById("id_texte");
  var champHtml = document.getElementById("id_corps_html");
  if (!zone || !texte || !champHtml) return;

  var EMOJIS = ["🙂", "😀", "😉", "😊", "👍", "🙏", "👏", "💪", "🎉", "✅", "❌", "⚠️", "📎", "📅", "⏰",
                "📞", "✉️", "🚜", "🌾", "🌱", "☀️", "🌧️", "💡", "🔧", "📊", "💰", "🤝", "❤️", "🥳"];

  function echapper(t) {
    return t.replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; });
  }

  // Le brouillon (signature, message cité) arrive en texte : on le montre tel quel, ligne à ligne.
  zone.innerHTML = champHtml.value || echapper(texte.value).replace(/\n/g, "<br>");
  editeur.hidden = false;
  texte.hidden = true;
  texte.setAttribute("aria-hidden", "true");

  function agir(commande, valeur) {
    zone.focus();
    document.execCommand(commande, false, valeur || null);
  }

  editeur.querySelectorAll("[data-commande]").forEach(function (bouton) {
    // mousedown : on garde la sélection du texte, que le clic ferait perdre.
    bouton.addEventListener("mousedown", function (evenement) {
      evenement.preventDefault();
      agir(bouton.dataset.commande, bouton.dataset.valeur);
    });
  });

  var taille = editeur.querySelector("[data-taille]");
  if (taille) {
    taille.addEventListener("change", function () { agir("fontSize", taille.value); });
  }
  var couleur = editeur.querySelector("[data-couleur]");
  if (couleur) {
    couleur.addEventListener("input", function () { agir("foreColor", couleur.value); });
  }

  // --- Lien : un petit panneau plutôt qu'une fenêtre du navigateur ---
  var panneauLien = editeur.querySelector("[data-panneau-lien]");
  var champUrl = editeur.querySelector("[data-url]");
  var selection = null;
  editeur.querySelector("[data-lien]").addEventListener("mousedown", function (evenement) {
    evenement.preventDefault();
    var s = window.getSelection();
    selection = s.rangeCount ? s.getRangeAt(0).cloneRange() : null;
    panneauLien.hidden = false;
    champUrl.focus();
  });
  function fermerLien() { panneauLien.hidden = true; champUrl.value = ""; }
  editeur.querySelector("[data-lien-annuler]").addEventListener("click", fermerLien);
  editeur.querySelector("[data-lien-valider]").addEventListener("click", function () {
    var url = champUrl.value.trim();
    if (!/^https?:\/\//i.test(url)) { champUrl.focus(); return; }
    zone.focus();
    if (selection) {
      var s = window.getSelection();
      s.removeAllRanges();
      s.addRange(selection);
      if (selection.collapsed) document.execCommand("insertText", false, url);
      document.execCommand("createLink", false, url);
    }
    fermerLien();
  });
  champUrl.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); editeur.querySelector("[data-lien-valider]").click(); }
    if (e.key === "Escape") fermerLien();
  });

  // --- Émojis ---
  var boutonEmojis = editeur.querySelector("[data-emojis]");
  var panneauEmojis = editeur.querySelector("[data-panneau-emojis]");
  EMOJIS.forEach(function (emoji) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "redaction__emoji";
    b.textContent = emoji;
    b.addEventListener("mousedown", function (e) { e.preventDefault(); agir("insertText", emoji); });
    panneauEmojis.appendChild(b);
  });
  boutonEmojis.addEventListener("click", function () {
    panneauEmojis.hidden = !panneauEmojis.hidden;
    boutonEmojis.setAttribute("aria-expanded", String(!panneauEmojis.hidden));
  });
  document.addEventListener("click", function (e) {
    if (!panneauEmojis.hidden && !panneauEmojis.contains(e.target) && e.target !== boutonEmojis) {
      panneauEmojis.hidden = true;
      boutonEmojis.setAttribute("aria-expanded", "false");
    }
  });

  // --- Envoi : on dépose la mise en forme et sa version texte dans le formulaire ---
  // La version texte est fabriquée par le serveur, à partir de cette mise en forme.
  zone.closest("form").addEventListener("submit", function () {
    champHtml.value = zone.innerHTML;
    texte.value = "";
  });
})();

// --- Pièces jointes dans la barre d'envoi (trombone), avec la liste des fichiers choisis ---
(function () {
  var bloc = document.querySelector("[data-pieces]");
  var bouton = document.querySelector("[data-joindre]");
  if (!bloc || !bouton) return;
  var champ = bloc.querySelector('input[type="file"]');
  var liste = bloc.querySelector("[data-liste-pieces]");
  var libelle = bloc.querySelector("[data-pieces-libelle]");
  if (!champ || !liste) return;

  bouton.hidden = false;
  champ.hidden = true;
  libelle.hidden = true;
  bouton.addEventListener("click", function () { champ.click(); });

  // Le bandeau ne s'affiche que s'il a quelque chose à montrer : une erreur, la case du
  // message d'origine, ou au moins un fichier choisi.
  var toujours = bloc.querySelector(".erreur") || bloc.querySelector(".courriel__case");

  function poids(octets) {
    if (octets < 1024) return octets + " o";
    if (octets < 1024 * 1024) return Math.round(octets / 1024) + " Ko";
    return (octets / 1024 / 1024).toFixed(1).replace(".", ",") + " Mo";
  }

  function afficher() {
    liste.textContent = "";
    var fichiers = Array.prototype.slice.call(champ.files);
    liste.hidden = fichiers.length === 0;
    bloc.hidden = !toujours && fichiers.length === 0;
    var total = 0;
    fichiers.forEach(function (fichier, rang) {
      total += fichier.size;
      var li = document.createElement("li");
      li.className = "piece";
      li.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>'
        + '<span class="piece__nom"></span><span class="piece__poids"></span>';
      li.querySelector(".piece__nom").textContent = fichier.name;
      li.querySelector(".piece__poids").textContent = poids(fichier.size);
      var retirer = document.createElement("button");
      retirer.type = "button";
      retirer.className = "piece__retirer";
      retirer.setAttribute("aria-label", "Retirer " + fichier.name);
      retirer.textContent = "✕";
      retirer.addEventListener("click", function () {
        var reste = new DataTransfer();
        Array.prototype.slice.call(champ.files).forEach(function (f, i) { if (i !== rang) reste.items.add(f); });
        champ.files = reste.files;
        afficher();
      });
      li.appendChild(retirer);
      liste.appendChild(li);
    });
    if (fichiers.length) {
      var resume = document.createElement("li");
      resume.className = "pieces__total";
      resume.textContent = fichiers.length + " fichier" + (fichiers.length > 1 ? "s" : "") + " · " + poids(total)
        + (total > 20 * 1024 * 1024 ? " — au-delà des 20 Mo acceptés" : "");
      resume.classList.toggle("pieces__total--trop", total > 20 * 1024 * 1024);
      liste.appendChild(resume);
    }
  }

  champ.addEventListener("change", afficher);
  afficher();
})();

// --- Carnet d'adresses : complète À, Cc et Cci avec les correspondants déjà connus ---
(function () {
  var form = document.querySelector("[data-carnet]");
  if (!form) return;
  var champs = ["id_a", "id_copie", "id_copie_cachee"].map(function (id) { return document.getElementById(id); })
    .filter(Boolean);
  if (!champs.length) return;

  var promesse = null;
  function carnet() {
    if (!promesse) {
      promesse = fetch(form.dataset.carnet, { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (d) { return d.adresses || []; })
        .catch(function () { return []; });
    }
    return promesse;
  }

  function sansAccents(texte) {
    return texte.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function ecrire(fiche) {
    if (!fiche.nom) return fiche.adresse;
    var nom = /[,;<>"]/.test(fiche.nom) ? '"' + fiche.nom.replace(/"/g, "") + '"' : fiche.nom;
    return nom + " <" + fiche.adresse + ">";
  }

  champs.forEach(function (champ, rang) {
    var liste = document.createElement("ul");
    liste.className = "carnet";
    liste.id = "carnet-" + rang;
    liste.setAttribute("role", "listbox");
    liste.hidden = true;
    champ.parentNode.classList.add("carnet-hote");
    champ.parentNode.insertBefore(liste, champ.nextSibling);
    champ.setAttribute("role", "combobox");
    champ.setAttribute("aria-autocomplete", "list");
    champ.setAttribute("aria-expanded", "false");
    champ.setAttribute("aria-controls", liste.id);
    champ.setAttribute("autocomplete", "off");

    var propositions = [], actif = -1;

    // Le champ accepte plusieurs adresses : seul le fragment en cours de frappe est complété.
    function segments() { return champ.value.split(/[,;]/); }
    function fragment() { return segments()[segments().length - 1].trim(); }

    function fermer() {
      liste.hidden = true;
      liste.textContent = "";
      propositions = [];
      actif = -1;
      champ.setAttribute("aria-expanded", "false");
      champ.removeAttribute("aria-activedescendant");
    }

    function surligner() {
      Array.prototype.forEach.call(liste.children, function (li, i) {
        li.classList.toggle("carnet__item--actif", i === actif);
        li.setAttribute("aria-selected", i === actif ? "true" : "false");
      });
      if (actif >= 0) {
        champ.setAttribute("aria-activedescendant", liste.children[actif].id);
        liste.children[actif].scrollIntoView({ block: "nearest" });
      } else {
        champ.removeAttribute("aria-activedescendant");
      }
    }

    function choisir(fiche) {
      var parties = segments();
      parties[parties.length - 1] = " " + ecrire(fiche);
      champ.value = parties.join(",").replace(/^\s+/, "") + ", ";
      fermer();
      champ.focus();
    }

    function afficher(fiches) {
      liste.textContent = "";
      propositions = fiches;
      actif = -1;
      fiches.forEach(function (fiche, i) {
        var li = document.createElement("li");
        li.className = "carnet__item";
        li.id = liste.id + "-" + i;
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", "false");
        var nom = document.createElement("span");
        nom.className = "carnet__nom";
        nom.textContent = fiche.nom || fiche.adresse;
        li.appendChild(nom);
        if (fiche.nom) {
          var adresse = document.createElement("span");
          adresse.className = "carnet__adresse";
          adresse.textContent = fiche.adresse;
          li.appendChild(adresse);
        }
        if (fiche.detail) {
          var detail = document.createElement("span");
          detail.className = "carnet__detail";
          detail.textContent = fiche.detail;
          li.appendChild(detail);
        }
        if (fiche.origine === "contact") {
          var marque = document.createElement("span");
          marque.className = "carnet__marque";
          marque.textContent = "Fiche";
          li.appendChild(marque);
        }
        // mousedown plutôt que click : le blur du champ ne doit pas fermer la liste avant.
        li.addEventListener("mousedown", function (e) { e.preventDefault(); choisir(fiche); });
        liste.appendChild(li);
      });
      liste.hidden = fiches.length === 0;
      champ.setAttribute("aria-expanded", fiches.length ? "true" : "false");
    }

    function chercher() {
      var terme = sansAccents(fragment());
      var deja = segments().slice(0, -1).map(function (p) { return sansAccents(p); }).join(" ");
      carnet().then(function (fiches) {
        if (document.activeElement !== champ) return;
        var trouvees = fiches.filter(function (f) {
          if (deja.indexOf(f.adresse) !== -1) return false;  // déjà dans le champ
          if (!terme) return true;
          return sansAccents(f.adresse).indexOf(terme) !== -1 || sansAccents(f.nom || "").indexOf(terme) !== -1
            || sansAccents(f.detail || "").indexOf(terme) !== -1;
        });
        afficher(trouvees.slice(0, 8));
      });
    }

    champ.addEventListener("input", chercher);
    champ.addEventListener("focus", chercher);
    champ.addEventListener("blur", function () { window.setTimeout(fermer, 120); });
    champ.addEventListener("keydown", function (e) {
      if (liste.hidden || !propositions.length) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        actif = (actif + (e.key === "ArrowDown" ? 1 : propositions.length) ) % propositions.length;
        surligner();
      } else if ((e.key === "Enter" || e.key === "Tab") && actif >= 0) {
        e.preventDefault();
        choisir(propositions[actif]);
      } else if (e.key === "Escape") {
        fermer();
      }
    });
  });
})();

// --- Objet proposé par l'assistant, d'après le brouillon ---
(function () {
  var form = document.querySelector("[data-objet-ia]");
  var bouton = document.querySelector("[data-objet-bouton]");
  var sujet = document.getElementById("id_sujet");
  var panneau = document.querySelector("[data-objet-propositions]");
  if (!form || !bouton || !sujet || !panneau) return;
  var libelle = bouton.querySelector("[data-libelle]");
  var zone = document.querySelector("[data-zone]");
  var texte = document.getElementById("id_texte");
  var jeton = form.querySelector("[name=csrfmiddlewaretoken]");
  var avant = null;

  bouton.hidden = false;

  function corps() {
    var editeur = document.querySelector("[data-editeur]");
    var brut = (editeur && !editeur.hidden && zone) ? zone.innerText : (texte ? texte.value : "");
    return brut.replace(/\u00a0/g, " ").trim();
  }

  function message(contenu, erreur) {
    panneau.textContent = "";
    panneau.hidden = !contenu;
    panneau.classList.toggle("courriel__propositions--erreur", !!erreur);
    if (contenu) panneau.appendChild(document.createTextNode(contenu));
  }

  function annulable() {
    var annuler = document.createElement("button");
    annuler.type = "button";
    annuler.className = "courriel__proposition courriel__proposition--discret";
    annuler.textContent = "Annuler";
    annuler.addEventListener("click", function () {
      if (avant !== null) sujet.value = avant;
      avant = null;
      message("");
    });
    return annuler;
  }

  function proposer(objets) {
    panneau.textContent = "";
    panneau.hidden = false;
    panneau.classList.remove("courriel__propositions--erreur");
    var intro = document.createElement("span");
    intro.className = "courriel__propositions-intro";
    intro.textContent = sujet.value.trim() ? "Reformulations proposées :" : "Objets proposés :";
    panneau.appendChild(intro);
    objets.forEach(function (objet) {
      var choix = document.createElement("button");
      choix.type = "button";
      choix.className = "courriel__proposition";
      choix.textContent = objet;
      choix.addEventListener("click", function () {
        if (avant === null) avant = sujet.value;
        sujet.value = objet;
        message("Objet remplacé. ");
        panneau.appendChild(annulable());
      });
      panneau.appendChild(choix);
    });
  }

  bouton.addEventListener("click", function () {
    var brouillon = corps();
    if (!brouillon) {
      message("Écrivez d'abord votre message : l'objet en découle.", true);
      return;
    }
    bouton.disabled = true;
    libelle.textContent = "L'assistant cherche…";
    message("");

    var donnees = new FormData();
    donnees.append("sujet", sujet.value);
    donnees.append("corps", brouillon);
    donnees.append("a", document.getElementById("id_a") ? document.getElementById("id_a").value : "");

    fetch(form.dataset.objetIa, {
      method: "POST",
      headers: { "X-CSRFToken": jeton ? jeton.value : "" },
      body: donnees,
      credentials: "same-origin"
    })
      .then(function (reponse) { return reponse.json().catch(function () { return {}; }); })
      .then(function (resultat) {
        if (resultat.objets && resultat.objets.length) proposer(resultat.objets);
        else message(resultat.erreur || "L'assistant est indisponible pour le moment.", true);
      })
      .catch(function () { message("Impossible de contacter l'assistant.", true); })
      .then(function () {
        bouton.disabled = false;
        libelle.textContent = "Proposer un objet";
      });
  });
})();

// --- Signature : on en change comme on change de boîte d'envoi ---
// Le bloc vit dans le message, repéré par data-signature ; la citation du message
// d'origine par data-origine, pour que la signature reste au-dessus d'elle.
(function () {
  var donnees = document.getElementById("signatures");
  var boite = document.getElementById("id_compte");
  var bloc = document.querySelector("[data-signature-bloc]");
  var choix = document.querySelector("[data-signature-choix]");
  var zone = document.querySelector("[data-zone]");
  if (!donnees || !boite || !bloc || !choix || !zone) return;
  var signatures = JSON.parse(donnees.textContent);
  if (!signatures.length) return;

  function trouver(pk) {
    return signatures.filter(function (s) { return String(s.pk) === String(pk); })[0] || null;
  }

  function disponibles(compte) {
    return signatures.filter(function (s) { return s.compte === null || String(s.compte) === String(compte); });
  }

  function appliquer(pk) {
    var present = zone.querySelector("[data-signature]");
    var signature = trouver(pk);
    if (!signature) {
      if (present) present.parentNode.removeChild(present);
      return;
    }
    if (!present) {
      present = document.createElement("div");
      var origine = zone.querySelector("[data-origine]");
      if (origine) zone.insertBefore(present, origine);
      else zone.appendChild(present);
    }
    present.setAttribute("data-signature", signature.pk);
    present.innerHTML = signature.html;
  }

  function remplir(compte, choisie) {
    var possibles = disponibles(compte);
    choix.textContent = "";
    choix.appendChild(new Option("Sans signature", ""));
    possibles.forEach(function (s) { choix.appendChild(new Option(s.libelle, String(s.pk))); });
    var retenue = "";
    if (choisie && possibles.some(function (s) { return String(s.pk) === String(choisie); })) {
      retenue = String(choisie);  // la signature en place reste valable pour cette boîte
    } else {
      var defaut = possibles.filter(function (s) { return s.defaut; })[0];
      retenue = defaut ? String(defaut.pk) : "";
    }
    choix.value = retenue;
    bloc.hidden = possibles.length === 0;
    return retenue;
  }

  var enPlace = zone.querySelector("[data-signature]");
  remplir(boite.value, enPlace ? enPlace.getAttribute("data-signature") : null);

  boite.addEventListener("change", function () {
    appliquer(remplir(boite.value, choix.value));
  });
  choix.addEventListener("change", function () { appliquer(choix.value); });
})();

// --- Reformulation du message par l'assistant ---
// Seul le texte écrit par l'auteur part : ni la signature, ni le message cité.
(function () {
  var form = document.querySelector("[data-reformuler-url]");
  var bouton = document.querySelector("button[data-reformuler]");
  var etat = document.querySelector("[data-reformuler-etat]");
  var zone = document.querySelector("[data-zone]");
  if (!form || !bouton || !etat || !zone) return;
  var libelle = bouton.querySelector("[data-libelle]");
  var jeton = form.querySelector("[name=csrfmiddlewaretoken]");
  var avant = null;

  bouton.hidden = false;

  function aPart(noeud) {
    return noeud.nodeType === 1 && (noeud.hasAttribute("data-signature") || noeud.hasAttribute("data-origine"));
  }

  function morceaux() {
    return Array.prototype.filter.call(zone.childNodes, function (n) { return !aPart(n); });
  }

  function brouillon() {
    // innerText restitue les sauts de ligne tels qu'ils sont affichés : il faut donc
    // que la copie soit rendue, d'où le passage hors écran plutôt que caché.
    var copie = document.createElement("div");
    copie.style.cssText = "position:absolute;left:-9999px;top:0;width:40rem;white-space:pre-wrap";
    morceaux().forEach(function (n) { copie.appendChild(n.cloneNode(true)); });
    document.body.appendChild(copie);
    var texte = copie.innerText.replace(/\u00a0/g, " ").trim();
    document.body.removeChild(copie);
    return texte;
  }

  function enParagraphes(texte) {
    var fragment = document.createDocumentFragment();
    texte.split(/\n{2,}/).forEach(function (bloc) {
      var p = document.createElement("p");
      bloc.split("\n").forEach(function (ligne, rang) {
        if (rang) p.appendChild(document.createElement("br"));
        p.appendChild(document.createTextNode(ligne));
      });
      fragment.appendChild(p);
    });
    return fragment;
  }

  function message(contenu, erreur) {
    etat.textContent = contenu || "";
    etat.hidden = !contenu;
    etat.classList.toggle("courriel__ia-etat--erreur", !!erreur);
  }

  function remplacer(texte) {
    var reste = morceaux();
    var suite = reste.length ? reste[reste.length - 1].nextSibling : zone.firstChild;
    reste.forEach(function (n) { zone.removeChild(n); });
    zone.insertBefore(enParagraphes(texte), suite);
  }

  bouton.addEventListener("click", function () {
    var texte = brouillon();
    if (!texte) {
      message("Écrivez d'abord votre message.", true);
      return;
    }
    bouton.disabled = true;
    libelle.textContent = "Reformulation en cours…";
    message("");

    var donnees = new FormData();
    donnees.append("corps", texte);

    fetch(form.dataset.reformulerUrl, {
      method: "POST",
      headers: { "X-CSRFToken": jeton ? jeton.value : "" },
      body: donnees,
      credentials: "same-origin"
    })
      .then(function (reponse) { return reponse.json().catch(function () { return {}; }); })
      .then(function (resultat) {
        if (!resultat.texte) {
          message(resultat.erreur || "L'assistant est indisponible pour le moment.", true);
          return;
        }
        avant = zone.innerHTML;
        remplacer(resultat.texte);
        message("Message reformulé. ");
        var annuler = document.createElement("button");
        annuler.type = "button";
        annuler.className = "courriel__proposition courriel__proposition--discret";
        annuler.textContent = "Annuler";
        annuler.addEventListener("click", function () {
          if (avant !== null) zone.innerHTML = avant;
          avant = null;
          message("");
        });
        etat.appendChild(annuler);
      })
      .catch(function () { message("Impossible de contacter l'assistant.", true); })
      .then(function () {
        bouton.disabled = false;
        libelle.textContent = "Reformuler avec l'IA";
      });
  });
})();
