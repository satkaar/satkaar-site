// Satkaar — petites interactions : menu mobile + header scrolled.
(function () {
    const header = document.getElementById('site-header');
    const toggle = document.querySelector('.site-nav__toggle');
    const menu = document.getElementById('primary-menu');

    // --- Menu mobile ---
    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            const open = menu.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            toggle.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
        });
        menu.querySelectorAll('a').forEach((a) =>
            a.addEventListener('click', () => {
                menu.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
            })
        );
    }

    // --- Header sticky : ombre légère au scroll ---
    function onScroll() {
        if (!header) return;
        if (window.scrollY > 8) header.classList.add('is-scrolled');
        else header.classList.remove('is-scrolled');
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
})();
