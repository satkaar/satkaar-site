import osoWebApp from "../config/oso-web-app.json";

/**
 * Site configuration
 */
export const siteConfig = {
  name: "O.S.O",
  description: "La gestion de documents simplifiée par l'IA. Une solution développée en France pour simplifier l'administratif de tous.",
  url: "https://oso-app.com",
  ogImage: "/og-image.png",
  links: {
    /** App web OSO — source unique : config/oso-web-app.json (lue aussi par Terraform bienvenue). */
    osoWebApp: osoWebApp.oso_web_app_url,
    appStore: "https://apps.apple.com/app/oso",
    playStore: "https://play.google.com/store/apps/details?id=com.oso",
    twitter: "https://twitter.com/oso_app",
    linkedin: "https://linkedin.com/company/oso-app",
    instagram: "https://instagram.com/oso_app",
    facebook: "https://facebook.com/oso.app",
  },
  contact: {
    email: "contact@oso-app.com",
    support: "support@oso-app.com",
  },
};

/**
 * Navigation links
 */
export const navLinks = [
  { label: "Accueil", href: "/" },
  { label: "Comment ça marche?", href: "/comment-ca-marche" },
  { label: "Pour qui?", href: "/pour-qui" },
  { label: "Fonctionnalités", href: "/fonctionnalites" },
  { label: "Sécurité", href: "/securite" },
] as const;

/**
 * Footer links
 */
export const footerLinks = {
  produits: [
    { label: "Fonctionnalités", href: "/fonctionnalites" },
    { label: "Comment ça marche?", href: "/comment-ca-marche" },
    { label: "Tarifs", href: "/#tarifs" },
    { label: "Télécharger l'app", href: "/#download" },
  ],
  legal: [
    { label: "Mentions légales", href: "/mentions-legales" },
    { label: "Politique de confidentialité", href: "/confidentialite" },
    { label: "CGU / CGV", href: "/cgu" },
    { label: "Gestion des cookies", href: "/cookies" },
    { label: "Vos droits", href: "/droits" },
  ],
};

/**
 * Target audience profiles
 */
export const targetProfiles = [
  {
    id: "independant",
    label: "Indépendant",
    shortLabel: "Indépendant",
  },
  {
    id: "freelance",
    label: "Freelances & consultants",
    shortLabel: "Freelances",
  },
  {
    id: "particulier",
    label: "Particuliers & Familles",
    shortLabel: "Particuliers",
  },
  {
    id: "senior",
    label: "Seniors & aidants",
    shortLabel: "Seniors",
  },
  {
    id: "etudiant",
    label: "Étudiants",
    shortLabel: "Étudiants",
  },
] as const;

/**
 * Process steps
 */
export const processSteps = [
  {
    id: "scan",
    title: "Scan",
    subtitle: "Une photo. C'est fait.",
    description: "Factures, reçus, contrats : O.S.O scanne en 3 secondes, corrige automatiquement et livre un document net, prêt à l'usage.",
    color: "vert",
  },
  {
    id: "tri",
    title: "Tri",
    subtitle: "Tout se classe tout seul.",
    description: "OSO comprend vos documents, extrait l'essentiel et les range automatiquement. Vous validez en un tap.",
    color: "jaune",
  },
  {
    id: "partage",
    title: "Partage",
    subtitle: "Envoyez. Au bon moment.",
    description: "Le bon document, au bon format, au bon destinataire. Mail, SMS ou cloud — en un seul tap.",
    color: "bleu-light",
  },
] as const;
