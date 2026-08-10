/**
 * Datenmodell des Prototypen.
 *
 * Die Typen sind bewusst nah an dem gehalten, was eine spätere echte Datenquelle
 * (Marktdaten-Partner, interner Presse-Feed) liefern könnte. Solange keine
 * Datenfreigabe vorliegt, werden sie ausschließlich mit synthetischen
 * Beispieldaten befüllt — siehe scripts/generate-demo-data.mjs und /methodik.
 */

export type RegionType = "district" | "city" | "region";

export type Region = {
  id: string;
  name: string;
  /** Bundesland */
  state: string;
  type: RegionType;
  description: string;
};

/**
 * Ein Monatswert je Region. Einzelne Kennzahlen können fehlen (null) —
 * die UI muss das als „[Keine Daten verfügbar]" ausweisen und darf nicht
 * auf 0 ausweichen.
 */
export type MarketObservation = {
  regionId: string;
  /** Periode im Format YYYY-MM */
  period: string;
  /** Angebotspreis Kauf, Euro je m² */
  salePricePerSqm: number | null;
  /** Angebotsmiete, Euro je m² und Monat */
  rentPricePerSqm: number | null;
  /** Anzahl der Inserate in der Periode */
  listingsCount: number | null;
  /** Durchschnittliche Wohnungsgröße in m² */
  averageSizeSqm: number | null;
};

export type EditorialInsight = {
  id: string;
  /** Ohne regionId: übergreifende Einordnung für die ganze Ausgabe */
  regionId?: string;
  period: string;
  title: string;
  summary: string;
  body: string;
  isDemo: boolean;
};

export type ReportIssue = {
  id: string;
  title: string;
  /** ISO-Datum */
  publicationDate: string;
  /** Periode, auf die sich die Ausgabe bezieht (YYYY-MM) */
  period: string;
  summary: string;
  featuredRegionIds: string[];
  isDemo: boolean;
};

export type DataSourceInfo = {
  name: string;
  status: "demo" | "planned" | "verified";
  /** ISO-Datum des letzten Datenstands */
  lastUpdated: string;
  methodologyNote: string;
};

/** Kennzahlen, die über die Zeit verglichen werden können. */
export type MetricKey =
  | "salePricePerSqm"
  | "rentPricePerSqm"
  | "listingsCount"
  | "averageSizeSqm";
