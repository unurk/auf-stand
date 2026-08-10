import { describe, expect, it } from "vitest";
import type { MarketObservation } from "@/data/types";
import {
  averageAcrossRegions,
  changeVsFirst,
  changeVsPrevious,
  compareRegions,
  hasData,
  latestWithValue,
  metricValue,
  priceToRentRatio,
  rankByChange,
  rankByLevel,
  relativeToAverage,
} from "./metrics";

function observation(
  period: string,
  values: Partial<Omit<MarketObservation, "regionId" | "period">> = {},
): MarketObservation {
  return {
    regionId: "test",
    period,
    salePricePerSqm: null,
    rentPricePerSqm: null,
    listingsCount: null,
    averageSizeSqm: null,
    ...values,
  };
}

describe("changeVsPrevious", () => {
  it("berechnet absolute und relative Veränderung der beiden jüngsten Perioden", () => {
    const series = [
      observation("2026-04", { salePricePerSqm: 1000 }),
      observation("2026-05", { salePricePerSqm: 1000 }),
      observation("2026-06", { salePricePerSqm: 1100 }),
    ];
    const change = changeVsPrevious(series, "salePricePerSqm");
    expect(change).not.toBeNull();
    expect(change?.absolute).toBe(100);
    expect(change?.percent).toBeCloseTo(10);
    expect(change?.fromPeriod).toBe("2026-05");
    expect(change?.toPeriod).toBe("2026-06");
  });

  it("überspringt Lücken und vergleicht die beiden jüngsten Perioden mit Wert", () => {
    const series = [
      observation("2026-04", { salePricePerSqm: 200 }),
      observation("2026-05"),
      observation("2026-06", { salePricePerSqm: 250 }),
    ];
    const change = changeVsPrevious(series, "salePricePerSqm");
    expect(change?.fromPeriod).toBe("2026-04");
    expect(change?.percent).toBeCloseTo(25);
  });

  it("liefert null, wenn weniger als zwei Werte vorliegen", () => {
    expect(
      changeVsPrevious([observation("2026-06", { salePricePerSqm: 100 })], "salePricePerSqm"),
    ).toBeNull();
    expect(changeVsPrevious([], "salePricePerSqm")).toBeNull();
  });

  it("liefert null statt Division durch null", () => {
    const series = [
      observation("2026-05", { listingsCount: 0 }),
      observation("2026-06", { listingsCount: 12 }),
    ];
    expect(changeVsPrevious(series, "listingsCount")).toBeNull();
  });
});

describe("changeVsFirst", () => {
  it("misst gegen die erste Periode mit Wert", () => {
    const series = [
      observation("2026-01"),
      observation("2026-02", { rentPricePerSqm: 10 }),
      observation("2026-06", { rentPricePerSqm: 12 }),
    ];
    const change = changeVsFirst(series, "rentPricePerSqm");
    expect(change?.fromPeriod).toBe("2026-02");
    expect(change?.percent).toBeCloseTo(20);
  });

  it("liefert null, wenn nur eine Periode Werte hat", () => {
    expect(
      changeVsFirst([observation("2026-06", { rentPricePerSqm: 12 })], "rentPricePerSqm"),
    ).toBeNull();
  });
});

describe("averageAcrossRegions", () => {
  it("lässt Regionen ohne Wert aus, statt sie als 0 zu zählen", () => {
    const average = averageAcrossRegions(
      {
        a: [observation("2026-06", { salePricePerSqm: 1000 })],
        b: [observation("2026-06", { salePricePerSqm: 2000 })],
        c: [observation("2026-06")],
      },
      "salePricePerSqm",
    );
    expect(average).toBe(1500);
  });

  it("liefert null, wenn gar kein Wert vorhanden ist", () => {
    expect(
      averageAcrossRegions({ a: [observation("2026-06")] }, "salePricePerSqm"),
    ).toBeNull();
  });
});

describe("Reihungen", () => {
  const series = {
    teuer: [observation("2026-06", { salePricePerSqm: 7000 })],
    mittel: [observation("2026-06", { salePricePerSqm: 4000 })],
    ohne: [observation("2026-06")],
    steigend: [
      observation("2026-05", { salePricePerSqm: 1000 }),
      observation("2026-06", { salePricePerSqm: 1200 }),
    ],
  };

  it("reiht absteigend nach Niveau und lässt Regionen ohne Wert weg", () => {
    const ranking = rankByLevel(series, "salePricePerSqm");
    expect(ranking.map((entry) => entry.regionId)).toEqual([
      "teuer",
      "mittel",
      "steigend",
    ]);
  });

  it("reiht absteigend nach prozentualer Veränderung", () => {
    const ranking = rankByChange(series, "salePricePerSqm", "previous");
    expect(ranking[0].regionId).toBe("steigend");
    expect(ranking[0].change.percent).toBeCloseTo(20);
  });
});

describe("relativeToAverage", () => {
  it("misst den Abstand zum Mittel aller Regionen in Prozent", () => {
    const all = {
      a: [observation("2026-06", { salePricePerSqm: 1000 })],
      b: [observation("2026-06", { salePricePerSqm: 3000 })],
    };
    expect(relativeToAverage(all.a, all, "salePricePerSqm")).toBeCloseTo(-50);
  });
});

describe("priceToRentRatio", () => {
  it("teilt den Kaufpreis durch die Jahresmiete", () => {
    expect(
      priceToRentRatio(
        observation("2026-06", { salePricePerSqm: 6000, rentPricePerSqm: 20 }),
      ),
    ).toBeCloseTo(25);
  });

  it("liefert null, wenn die Miete fehlt", () => {
    expect(
      priceToRentRatio(observation("2026-06", { salePricePerSqm: 6000 })),
    ).toBeNull();
  });
});

describe("compareRegions", () => {
  it("bildet die Vereinigungsmenge der Perioden und markiert Lücken als null", () => {
    const rows = compareRegions(
      {
        a: [
          observation("2026-05", { listingsCount: 10 }),
          observation("2026-06", { listingsCount: 12 }),
        ],
        b: [observation("2026-06", { listingsCount: 5 })],
      },
      "listingsCount",
    );
    expect(rows.map((row) => row.period)).toEqual(["2026-05", "2026-06"]);
    expect(rows[0].values).toEqual({ a: 10, b: null });
    expect(rows[1].values).toEqual({ a: 12, b: 5 });
  });
});

describe("Hilfsfunktionen", () => {
  it("metricValue behandelt fehlende Beobachtungen und Werte als null", () => {
    expect(metricValue(undefined, "salePricePerSqm")).toBeNull();
    expect(metricValue(observation("2026-06"), "salePricePerSqm")).toBeNull();
  });

  it("latestWithValue findet den jüngsten vorhandenen Wert", () => {
    const series = [
      observation("2026-04", { rentPricePerSqm: 9 }),
      observation("2026-05", { rentPricePerSqm: 11 }),
      observation("2026-06"),
    ];
    expect(latestWithValue(series, "rentPricePerSqm")?.period).toBe("2026-05");
  });

  it("hasData erkennt vollständig leere Reihen", () => {
    expect(hasData([observation("2026-06")], "rentPricePerSqm")).toBe(false);
    expect(
      hasData([observation("2026-06", { rentPricePerSqm: 1 })], "rentPricePerSqm"),
    ).toBe(true);
  });
});
