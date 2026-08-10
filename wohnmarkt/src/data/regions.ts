import type { Region } from "./types";

/**
 * Demo-Auswahl von acht Regionen. Zuschnitt und Beschreibung sind für den
 * Prototypen gesetzt und können später durch die Regionsschlüssel einer
 * echten Datenquelle ersetzt werden — die ids sind dafür stabil gehalten.
 */
export const regions: Region[] = [
  {
    id: "wien-neubau",
    name: "Wien Neubau",
    state: "Wien",
    type: "district",
    description:
      "Innerstädtischer Bezirk mit hohem Altbauanteil, kleinteiliger Struktur und traditionell wenig Neubauvolumen.",
  },
  {
    id: "wien-donaustadt",
    name: "Wien Donaustadt",
    state: "Wien",
    type: "district",
    description:
      "Flächenbezirk am östlichen Stadtrand mit ausgeprägter Neubautätigkeit und vergleichsweise großen Wohnungen.",
  },
  {
    id: "graz",
    name: "Graz",
    state: "Steiermark",
    type: "city",
    description:
      "Zweitgrößte Stadt Österreichs, starker Universitätsstandort mit entsprechend hoher Nachfrage nach kleinen Einheiten.",
  },
  {
    id: "salzburg-stadt",
    name: "Salzburg Stadt",
    state: "Salzburg",
    type: "city",
    description:
      "Enger Talkessel mit knappem Baulandangebot; das Preisniveau liegt seit Jahren deutlich über dem Bundesschnitt.",
  },
  {
    id: "linz",
    name: "Linz",
    state: "Oberösterreich",
    type: "city",
    description:
      "Industrie- und Verwaltungsstandort mit breitem Wohnungsbestand und aktivem gemeinnützigem Wohnbau.",
  },
  {
    id: "innsbruck",
    name: "Innsbruck",
    state: "Tirol",
    type: "city",
    description:
      "Alpine Landeshauptstadt mit begrenzter Siedlungsfläche und zusätzlicher Nachfrage aus Tourismus und Universität.",
  },
  {
    id: "st-poelten",
    name: "St. Pölten",
    state: "Niederösterreich",
    type: "city",
    description:
      "Landeshauptstadt im Wiener Umland mit guter Bahnanbindung — ein typischer Ausweichstandort für Pendler:innen.",
  },
  {
    id: "klagenfurt",
    name: "Klagenfurt",
    state: "Kärnten",
    type: "city",
    description:
      "Landeshauptstadt am Wörthersee mit moderatem Preisniveau und einem vergleichsweise kleinen Inseratsmarkt.",
  },
];
