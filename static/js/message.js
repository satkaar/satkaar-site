// Aides à la rédaction du message de contact : dictée vocale et reformulation par l'IA.
// Sans JavaScript, les aides restent masquées et le champ reste un simple texte libre.
(function () {
  var bloc = document.querySelector(".assistant-message");
  if (!bloc) return;

  var champ = bloc.querySelector("textarea");
  var boutonDicter = bloc.querySelector('[data-action="dicter"]');
  var libelleDicter = boutonDicter.querySelector("[data-libelle]");
  var boutonReformuler = bloc.querySelector('[data-action="reformuler"]');
  var libelleReformuler = boutonReformuler.querySelector("[data-libelle]");
  var etat = bloc.querySelector(".outils-message__etat");
  var jeton = champ.form.querySelector('[name="csrfmiddlewaretoken"]').value;

  bloc.querySelector(".outils-message").hidden = false;

  function annoncer(message, estErreur) {
    etat.textContent = message || "";
    etat.classList.toggle("outils-message__etat--erreur", Boolean(estErreur));
  }

  function ajusterHauteur() {
    champ.style.height = "auto";
    champ.style.height = champ.scrollHeight + 2 + "px";
  }

  champ.addEventListener("input", ajusterHauteur);

  // --- Dictée ----------------------------------------------------------------
  // Web Speech API : Chrome, Edge et Safari. Absente de Firefox : le bouton reste masqué.

  var Reconnaissance = window.SpeechRecognition || window.webkitSpeechRecognition;
  var reconnaissance = null;
  var texteDeBase = "";

  var ERREURS_DICTEE = {
    "not-allowed": "Accès au micro refusé. Autorisez-le dans votre navigateur pour dicter.",
    "service-not-allowed": "La dictée n'est pas autorisée dans ce navigateur.",
    "audio-capture": "Aucun micro détecté.",
    "no-speech": "Aucune voix détectée.",
    network: "Dictée indisponible (connexion réseau)."
  };

  function ecoute(active) {
    boutonDicter.setAttribute("aria-pressed", String(active));
    libelleDicter.textContent = active ? "Écoute…" : "Dicter";
  }

  function demarrerDictee() {
    annoncer("");
    reconnaissance = new Reconnaissance();
    reconnaissance.lang = "fr-FR";
    reconnaissance.continuous = true;
    reconnaissance.interimResults = true;
    texteDeBase = champ.value;

    reconnaissance.onresult = function (evenement) {
      var definitif = "";
      var provisoire = "";
      for (var i = evenement.resultIndex; i < evenement.results.length; i++) {
        var resultat = evenement.results[i];
        if (resultat.isFinal) definitif += resultat[0].transcript;
        else provisoire += resultat[0].transcript;
      }
      if (definitif) {
        texteDeBase = (texteDeBase ? texteDeBase.trimEnd() + " " : "") + definitif.trim();
      }
      champ.value = (texteDeBase + (provisoire ? " " + provisoire : "")).trimStart();
      ajusterHauteur();
    };

    reconnaissance.onerror = function (evenement) {
      if (evenement.error === "aborted") return;
      annoncer(ERREURS_DICTEE[evenement.error] || "La dictée s'est interrompue.", true);
    };

    reconnaissance.onend = function () {
      reconnaissance = null;
      champ.value = texteDeBase;
      ecoute(false);
    };

    try {
      reconnaissance.start();
      ecoute(true);
      if (window.satkaarMesure) window.satkaarMesure("dictee");
    } catch (e) {
      reconnaissance = null;
      annoncer("Impossible de démarrer la dictée. Autorisez l'accès au micro.", true);
    }
  }

  if (Reconnaissance) {
    boutonDicter.hidden = false;
    boutonDicter.addEventListener("click", function () {
      if (reconnaissance) reconnaissance.stop();
      else demarrerDictee();
    });
  }

  // --- Reformulation ---------------------------------------------------------
  // Comme dans le CRM, le texte est remplacé directement ; « Annuler » rend l'original.

  var texteOriginal = null;

  function annulerReformulation() {
    if (texteOriginal === null) return;
    champ.value = texteOriginal;
    texteOriginal = null;
    ajusterHauteur();
    annoncer("");
    champ.focus();
  }

  function reformuler() {
    var brouillon = champ.value.trim();
    if (!brouillon) {
      annoncer("Écrivez ou dictez d'abord votre message.", true);
      return;
    }
    if (reconnaissance) reconnaissance.stop();

    annoncer("");
    boutonReformuler.disabled = true;
    libelleReformuler.textContent = "Reformulation en cours…";

    var donnees = new FormData();
    donnees.append("message", brouillon);

    fetch(bloc.dataset.urlReformuler, {
      method: "POST",
      headers: { "X-CSRFToken": jeton },
      body: donnees,
      credentials: "same-origin"
    })
      .then(function (reponse) {
        return reponse.json().catch(function () {
          return {};
        });
      })
      .then(function (resultat) {
        if (!resultat.texte) {
          annoncer(resultat.erreur || "La reformulation est indisponible pour le moment.", true);
          return;
        }
        texteOriginal = champ.value;
        champ.value = resultat.texte;
        ajusterHauteur();
        etat.textContent = "Message reformulé. ";
        etat.classList.remove("outils-message__etat--erreur");
        var annuler = document.createElement("button");
        annuler.type = "button";
        annuler.className = "outils-message__annuler";
        annuler.textContent = "Annuler";
        annuler.addEventListener("click", annulerReformulation);
        etat.appendChild(annuler);
      })
      .catch(function () {
        annoncer("Impossible de contacter l'assistant IA.", true);
      })
      .then(function () {
        boutonReformuler.disabled = false;
        libelleReformuler.textContent = "✦ Reformuler avec l'IA";
      });
  }

  boutonReformuler.addEventListener("click", reformuler);
})();
