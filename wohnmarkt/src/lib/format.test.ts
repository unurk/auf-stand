import { describe, expect, it } from "vitest";
import {
  KEINE_DATEN,
  changeDirection,
  formatCount,
  formatDate,
  formatMetric,
  formatMetricDelta,
  formatPercent,
  formatPeriod,
  formatPeriodShort,
  formatSqm,
} from "./format";

/** Non-breaking spaces und schmale Leerzeichen der Intl-Ausgabe angleichen. */
const normalize = (value: string) => value.replace(/[  ]/g, " ");

describe("Fehlwerte", () => {
  it("gibt für null, undefined und NaN durchgängig denselben Text aus", () => {
    for (const value of [null, undefined, Number.NaN]) {
      expect(formatCount(value)).toBe(KEINE_DATEN);
      expect(formatPercent(value)).toBe(KEINE_DATEN);
      expect(formatSqm(value)).toBe(KEINE_DATEN);
      expect(formatMetric(value, "salePricePerSqm")).toBe(KEINE_DATEN);
      expect(formatMetricDelta(value, "listingsCount")).toBe(KEINE_DATEN);
    }
    expect(formatPeriod(undefined)).toBe(KEINE_DATEN);
    expect(formatDate(null)).toBe(KEINE_DATEN);
    expect(formatDate("kein-datum")).toBe(KEINE_DATEN);
  });

  it("formatiert 0 als Wert und nicht als Fehlwert", () => {
    expect(formatCount(0)).toBe("0");
    expect(normalize(formatPercent(0))).toBe("±0,0 %");
  });
});

describe("formatPercent", () => {
  it("setzt ein Vorzeichen und rundet auf eine Nachkommastelle", () => {
    expect(normalize(formatPercent(2.44))).toBe("+2,4 %");
    expect(normalize(formatPercent(-2.46))).toBe("−2,5 %");
  });
});

describe("formatPeriod", () => {
  it("übersetzt YYYY-MM in Monat und Jahr", () => {
    expect(formatPeriod("2026-06")).toBe("Juni 2026");
    expect(formatPeriod("2026-01")).toBe("Jänner 2026");
  });

  it("kürzt für Diagrammachsen", () => {
    expect(formatPeriodShort("2026-06")).toBe("06/26");
  });
});

describe("formatDate", () => {
  it("gibt ein österreichisch geschriebenes Datum aus", () => {
    expect(formatDate("2026-07-02")).toBe("2. Juli 2026");
  });
});

describe("formatMetric", () => {
  it("wählt Einheit und Genauigkeit passend zur Kennzahl", () => {
    expect(normalize(formatMetric(7240, "salePricePerSqm"))).toBe("7.240 € / m²");
    expect(normalize(formatMetric(17.4, "rentPricePerSqm"))).toBe("17,40 € / m²");
    expect(normalize(formatMetric(1240, "listingsCount"))).toBe("1.240");
    expect(normalize(formatMetric(68.4, "averageSizeSqm"))).toBe("68,4 m²");
  });

  it("setzt bei Deltas ein Vorzeichen vor den Betrag", () => {
    expect(normalize(formatMetricDelta(-30, "listingsCount"))).toBe("−30");
    expect(normalize(formatMetricDelta(30, "listingsCount"))).toBe("+30");
  });
});

describe("changeDirection", () => {
  it("unterscheidet Anstieg, Rückgang, Stillstand und Unbekanntes", () => {
    expect(changeDirection(1.2)).toBe("up");
    expect(changeDirection(-1.2)).toBe("down");
    expect(changeDirection(0)).toBe("flat");
    expect(changeDirection(null)).toBe("unknown");
  });
});
