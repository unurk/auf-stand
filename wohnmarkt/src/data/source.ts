import type { DataSourceInfo } from "./types";

/**
 * Einzige Quelle der Wahrheit für den Datenstatus. Die UI liest den Status
 * hier aus, statt „Demo" an vielen Stellen hart hineinzuschreiben.
 *
 * status:
 *   "demo"     — synthetische Beispieldaten (aktueller Stand des Prototypen)
 *   "planned"  — Quelle vereinbart, Anbindung noch offen
 *   "verified" — echte, freigegebene Daten
 */
export const dataSource: DataSourceInfo = {
  name: "Synthetische Beispieldaten (Prototyp)",
  status: "demo",
  lastUpdated: "2026-06-30",
  methodologyNote:
    "Die dargestellten Werte wurden für diesen Prototyp deterministisch erzeugt und bilden keinen realen Markt ab. Eine Datenquelle für Angebotsdaten ist noch [ZU PRÜFEN]; eine Datenpartnerschaft ist nicht vereinbart.",
};

/** Periode, auf die sich die aktuelle Ausgabe bezieht. */
export const currentPeriod = "2026-06";
