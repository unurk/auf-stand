import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getInsightForRegion,
  getObservations,
  getObservationsForRegions,
  getRegion,
  getRegions,
} from "@/data";
import {
  changeVsFirst,
  changeVsPrevious,
  latestWithValue,
  metricValue,
  priceToRentRatio,
  relativeToAverage,
} from "@/lib/metrics";
import {
  KEINE_DATEN,
  formatCount,
  formatDecimal,
  formatPercent,
  formatPeriod,
  formatRentPerSqm,
  formatSalePerSqm,
  formatSqm,
} from "@/lib/format";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { MetricTile } from "@/components/ui/MetricTile";
import { ChangeBadge } from "@/components/ui/ChangeBadge";
import { DemoBadge } from "@/components/ui/DemoBadge";
import { EditorialNote } from "@/components/ui/EditorialNote";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";
import { WatchButton } from "@/components/region/WatchButton";
import { RegionTimeSeries } from "@/components/region/RegionTimeSeries";

export function generateStaticParams() {
  return getRegions().map((region) => ({ regionId: region.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ regionId: string }>;
}): Promise<Metadata> {
  const { regionId } = await params;
  const region = getRegion(regionId);
  if (!region) return { title: "Region nicht gefunden" };
  return { title: region.name, description: region.description };
}

export default async function RegionDetailPage({
  params,
}: {
  params: Promise<{ regionId: string }>;
}) {
  const { regionId } = await params;
  const region = getRegion(regionId);
  if (!region) notFound();

  const series = getObservations(region.id);
  const allSeries = getObservationsForRegions(
    getRegions().map((entry) => entry.id),
  );

  const latest = series.at(-1);
  const latestSale = latestWithValue(series, "salePricePerSqm");

  const sale = metricValue(latestSale, "salePricePerSqm");
  const rent = metricValue(
    latestWithValue(series, "rentPricePerSqm"),
    "rentPricePerSqm",
  );
  const listings = metricValue(
    latestWithValue(series, "listingsCount"),
    "listingsCount",
  );
  const size = metricValue(
    latestWithValue(series, "averageSizeSqm"),
    "averageSizeSqm",
  );

  const saleVsAverage = relativeToAverage(series, allSeries, "salePricePerSqm");
  const ratio = priceToRentRatio(latest);

  return (
    <div className="space-y-10">
      <nav aria-label="Brotkrumen" className="text-sm text-ink-muted">
        <Link href="/regionen" className="underline underline-offset-2 hover:text-ink">
          Regionen
        </Link>
        <span aria-hidden="true"> › </span>
        <span className="text-ink">{region.name}</span>
      </nav>

      <header>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium tracking-wide text-accent uppercase">
            {region.state}
          </span>
          <DemoBadge />
        </div>
        <h1 className="mt-2 font-editorial text-3xl leading-tight text-ink sm:text-4xl">
          {region.name}
        </h1>
        <p className="mt-3 max-w-prose text-base leading-relaxed text-ink-soft">
          {region.description}
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <WatchButton regionId={region.id} regionName={region.name} />
          <span className="text-sm text-ink-muted">
            Datenstand: {formatPeriod(latest?.period)}
          </span>
        </div>
      </header>

      <section aria-labelledby="niveau-titel">
        <SectionHeading
          id="niveau-titel"
          title="Aktuelles Preisniveau"
          description="Alle Werte beziehen sich auf Angebotsdaten, nicht auf tatsächlich bezahlte Preise."
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricTile
            label="Angebotspreis Kauf"
            value={formatSalePerSqm(sale)}
            change={
              <ChangeBadge
                change={changeVsPrevious(series, "salePricePerSqm")}
                metric="salePricePerSqm"
                showAbsolute
              />
            }
            note="gegenüber Vorperiode"
          />
          <MetricTile
            label="Angebotsmiete"
            value={formatRentPerSqm(rent)}
            change={
              <ChangeBadge
                change={changeVsPrevious(series, "rentPricePerSqm")}
                metric="rentPricePerSqm"
              />
            }
            note="je m² und Monat"
            hint="Für die jüngsten Perioden liegen keine Mietwerte vor. Der Prototyp schreibt fehlende Werte nicht fort."
          />
          <MetricTile
            label="Inserate"
            value={formatCount(listings)}
            change={
              <ChangeBadge
                change={changeVsPrevious(series, "listingsCount")}
                metric="listingsCount"
              />
            }
            note="in der jüngsten Periode"
          />
          <MetricTile
            label="Ø Wohnungsgröße"
            value={formatSqm(size)}
            change={
              <ChangeBadge
                change={changeVsPrevious(series, "averageSizeSqm")}
                metric="averageSizeSqm"
              />
            }
            note="typische Größe im Angebot"
          />
        </div>
      </section>

      <section aria-labelledby="verlauf-titel">
        <SectionHeading
          id="verlauf-titel"
          title="Entwicklung über Zeit"
          description="Kennzahl und Zeitraum lassen sich umschalten. Fehlende Monate bleiben als Lücke sichtbar."
          aside={<DemoBadge />}
        />
        <RegionTimeSeries
          regionId={region.id}
          regionName={region.name}
          series={series}
        />
      </section>

      <section aria-labelledby="einordnen-titel">
        <SectionHeading
          id="einordnen-titel"
          title="Einordnung der Kennzahlen"
          description="Berechnete Verhältniswerte — jeweils mit der zugrunde liegenden Rechenregel benannt."
        />
        <div className="grid gap-3 sm:grid-cols-3">
          <MetricTile
            label="Kaufpreis ggü. Regionsschnitt"
            value={formatPercent(saleVsAverage)}
            note={`Abstand zum Mittelwert aller ${Object.keys(allSeries).length} Demo-Regionen`}
          />
          <MetricTile
            label="Kaufpreisfaktor"
            value={ratio === null ? KEINE_DATEN : `${formatDecimal(ratio)} Jahresmieten`}
            note="Kaufpreis je m² geteilt durch Jahresmiete je m²"
          />
          <MetricTile
            label="Kaufpreis seit Reihenbeginn"
            value={formatPercent(
              changeVsFirst(series, "salePricePerSqm")?.percent ?? null,
            )}
            note={`gegenüber ${formatPeriod(
              changeVsFirst(series, "salePricePerSqm")?.fromPeriod,
            )}`}
          />
        </div>
        <p className="mt-3 max-w-prose text-xs leading-relaxed text-ink-muted">
          Der Kaufpreisfaktor ist ein Verhältniswert aus Angebotsdaten und keine
          Renditeaussage: Nebenkosten, Leerstand, Instandhaltung und tatsächlich
          erzielte Preise sind darin nicht enthalten.
        </p>
      </section>

      <section aria-labelledby="analyse-titel">
        <SectionHeading
          id="analyse-titel"
          title="Redaktionelle Analyse"
          description="Deutung der Daten, klar getrennt von den Daten selbst."
        />
        <EditorialNote insight={getInsightForRegion(region.id)} />
      </section>

      <DataSourcePanel />
    </div>
  );
}
