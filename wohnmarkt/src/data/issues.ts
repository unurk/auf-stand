import type { ReportIssue } from "./types";

/**
 * Demo-Ausgaben des Wohnmarkt-Updates. Die Zusammenfassungen sind redaktionelle
 * Platzhaltertexte für den Prototypen — sie beschreiben die synthetischen Daten
 * und sind ausdrücklich keine Marktaussage.
 */
export const issues: ReportIssue[] = [
  {
    id: "2026-06",
    period: "2026-06",
    title: "Wohnmarkt-Update Juni 2026",
    publicationDate: "2026-07-02",
    summary:
      "In den beobachteten Regionen entwickeln sich Angebotspreise und Angebotsvolumen weiter auseinander: Die Mieten steigen in allen Demo-Regionen schneller als die Kaufpreise, während die Zahl der Inserate in den teuren Kernstädten zurückgeht.",
    featuredRegionIds: ["st-poelten", "salzburg-stadt", "klagenfurt"],
    isDemo: true,
  },
  {
    id: "2026-05",
    period: "2026-05",
    title: "Wohnmarkt-Update Mai 2026",
    publicationDate: "2026-06-03",
    summary:
      "Das Frühjahr bringt in den Beispieldaten mehr Inserate als der Jahresbeginn. Beim Kaufpreisniveau bleibt der Abstand zwischen den Landeshauptstädten und dem Wiener Umland weitgehend stabil.",
    featuredRegionIds: ["wien-donaustadt", "graz", "linz"],
    isDemo: true,
  },
  {
    id: "2026-04",
    period: "2026-04",
    title: "Wohnmarkt-Update April 2026",
    publicationDate: "2026-05-05",
    summary:
      "Erste Ausgabe des Prototypen: Sie ordnet das Preisniveau der acht Demo-Regionen zueinander ein und erklärt, warum Angebotspreise nicht mit tatsächlich bezahlten Preisen gleichzusetzen sind.",
    featuredRegionIds: ["wien-neubau", "innsbruck", "st-poelten"],
    isDemo: true,
  },
];
