// Mesure d'audience maison : sans cookie, sans service tiers, et rien si le visiteur refuse le suivi.
// Envoie à la sortie de page le temps actif, le défilement et les indicateurs de performance
// (LCP, CLS, INP, FCP, TTFB), ainsi que quelques clics utiles (téléphone, courriel, liens sortants…).
(function () {
  if (navigator.doNotTrack === "1" || window.globalPrivacyControl) return;
  if (/^\/(espace|admin)\//.test(location.pathname)) return;

  var chemin = location.pathname;

  function envoyer(donnees) {
    donnees.chemin = chemin;
    var corps = JSON.stringify(donnees);
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/mesure/", new Blob([corps], { type: "text/plain" }));
    } else {
      fetch("/mesure/", { method: "POST", body: corps, keepalive: true, credentials: "same-origin" });
    }
  }

  window.satkaarMesure = function (type, cible) {
    envoyer({ type: type, cible: cible || "" });
  };

  // --- Clics utiles ------------------------------------------------------------
  document.addEventListener("click", function (evenement) {
    var lien = evenement.target.closest ? evenement.target.closest("a") : null;
    if (!lien) return;
    var href = lien.getAttribute("href") || "";
    if (href.indexOf("tel:") === 0) {
      window.satkaarMesure("telephone", href.slice(4));
    } else if (href.indexOf("mailto:") === 0) {
      window.satkaarMesure("courriel", href.slice(7));
    } else if (lien.host && lien.host !== location.host) {
      window.satkaarMesure("sortant", lien.host);
    } else if (lien.classList.contains("bouton--primaire")) {
      window.satkaarMesure("appel_action", (lien.textContent || "").trim().slice(0, 80));
    }
  });

  document.addEventListener("toggle", function (evenement) {
    var bloc = evenement.target;
    if (bloc.classList && bloc.classList.contains("faq__item") && bloc.open) {
      window.satkaarMesure("faq", bloc.querySelector("summary").textContent.trim().slice(0, 160));
    }
  }, true);

  // --- Engagement --------------------------------------------------------------
  var defilement = 0;
  function mesurerDefilement() {
    var page = document.documentElement;
    var vu = ((page.scrollTop || document.body.scrollTop) + window.innerHeight) / page.scrollHeight * 100;
    defilement = Math.max(defilement, Math.min(100, Math.round(vu)));
  }
  window.addEventListener("scroll", mesurerDefilement, { passive: true });
  mesurerDefilement();

  var tempsActif = 0;
  var depuis = document.visibilityState === "visible" ? Date.now() : null;

  // --- Performance (Core Web Vitals) -------------------------------------------
  var perf = { lcp: null, cls: 0, inp: null, fcp: null, ttfb: null };
  function observer(type, rappel, options) {
    try {
      new PerformanceObserver(function (liste) { liste.getEntries().forEach(rappel); })
        .observe(Object.assign({ type: type, buffered: true }, options || {}));
    } catch (e) { /* type non pris en charge par ce navigateur */ }
  }
  observer("largest-contentful-paint", function (e) { perf.lcp = Math.round(e.startTime); });
  observer("layout-shift", function (e) { if (!e.hadRecentInput) perf.cls += e.value; });
  observer("paint", function (e) { if (e.name === "first-contentful-paint") perf.fcp = Math.round(e.startTime); });
  observer("event", function (e) {
    if (e.interactionId) perf.inp = Math.max(perf.inp || 0, Math.round(e.duration));
  }, { durationThreshold: 40 });
  var navigation = performance.getEntriesByType && performance.getEntriesByType("navigation")[0];
  if (navigation) perf.ttfb = Math.round(navigation.responseStart);

  // --- Envoi à la sortie de la page --------------------------------------------
  var envoye = false;
  function terminer() {
    if (depuis) { tempsActif += Date.now() - depuis; depuis = null; }
    if (envoye) return;
    envoye = true;
    envoyer({
      type: "page",
      temps_actif: Math.round(tempsActif / 1000),
      defilement: defilement,
      lcp: perf.lcp, cls: Math.round(perf.cls * 10000) / 10000, inp: perf.inp, fcp: perf.fcp, ttfb: perf.ttfb
    });
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") {
      terminer();
    } else if (!depuis) {
      depuis = Date.now();
    }
  });
  window.addEventListener("pagehide", terminer);
})();
