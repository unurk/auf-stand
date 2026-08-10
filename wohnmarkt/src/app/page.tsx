import Link from "next/link";
import {
  getCurrentIssue,
  getCurrentPeriod,
  getObservationsForRegions,
  getOverviewInsight,
  getRegions,
} from "@/data";
import { averageAcrossRegions } from "@/lib/metrics";
import { getHighlights, getPriceLevelRanking } from "@/lib/highlights";
import {
  formatCount,
  formatDate,
  formatMetric,
  formatPeriod,
  formatRentPerSqm,
  formatSalePerSqm,
  METRIC_LABELS,
} from "@/lib/format";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { MetricTile } from "@/components/ui/MetricTile";
import { ChangeBadge } from "@/components/ui/ChangeBadge";
import { DemoBadge } from "@/components/ui/DemoBadge";
import { EditorialNote } from "@/components/ui/EditorialNote";
import { EmptyState } from "@/components/ui/EmptyState";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";
import { AboCta } from "@/components/premium/AboCta";
import { WatchButton } from "@/components/region/WatchButton";
import { ComparisonBars } from "@/components/charts/ComparisonBars";

export default function DashboardPage() {
  const period = getCurrentPeriod();
  const issue = getCurrentIssue();
  const regions = getRegions();
  const series = getObservationsForRegions(regions.map((region) => region.id));
  const highlights = getHighlights();
  const ranking = getPriceLevelRanking();

  const averageSale = averageAcrossRegions(series, "salePricePerSqm");
  const averageRent = averageAcrossRegions(series, "rentPricePerSqm");
  const totalListings = Object.values(series).reduce((sum, entries) => {
    const latest = entries.at(-1)?.listingsCount;
    return sum + (typeof latest === "number" ? latest : 0);
  }, 0);

  return (
    <div className="space-y-10">
      <section aria-labelledby="ausgabe-titel">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium tracking-wide text-accent uppercase">
            Aktuelle Ausgabe
          </span>
          <DemoBadge />
        </div>
        <h1
          id="ausgabe-titel"
          className="mt-2 font-editorial text-3xl leading-tight text-ink sm:text-4xl"
        >
          {issue ? issue.title : `Wohnmarkt-Update ${formatPeriod(period)}`}
        </h1>
        {issue && (
          <>
            <p className="mt-1 text-sm text-ink-muted">
              Veröffentlicht am {formatDate(issue.publicationDate)} · Datenstand{" "}
              {formatPeriod(issue.period)}
            </p>
            <p className="mt-4 max-w-prose font-editorial text-lg leading-relaxed text-ink-soft">
              {issue.summary}
            </p>
          </>
        )}
      </section>

      <section aria-labelledby="ueberblick-titel">
        <SectionHeading
          id="ueberblick-titel"
          title="Der Markt in Zahlen"
          description={`Durchschnitt über alle ${regions.length} Demo-Regionen, Stand ${formatPeriod(period)}.`}
        />
        <div className="grid gap-3 sm:grid-cols-3">
          <MetricTile
            label="Ø Angebotspreis Kauf"
            value={formatSalePerSqm(averageSale)}
            note={`Mittelwert über ${regions.length} Regionen`}
          />
          <MetricTile
            label="Ø Angebotsmiete"
            value={formatRentPerSqm(averageRent)}
            note="Je m² und Monat"
          />
          <MetricTile
            label="Inserate gesamt"
            value={formatCount(totalListings)}
            note="Summe der jüngsten Periode"
          />
        </div>
      </section>

      <section aria-labelledby="bewegungen-titel">
        <SectionHeading
          id="bewegungen-titel"
          title="Wichtigste Bewegungen"
          description="Abgeleitet aus definierten Reihungen über die letzten zwölf Monate — keine Wertung, keine Prognose."
          aside={<DemoBadge />}
        />
        {highlights.length === 0 ? (
          <EmptyState
            title="Keine Bewegungen berechenbar"
            description="Für den gewählten Zeitraum liegen zu wenige Datenpunkte vor, um Veränderungen zu berechnen."
          />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {highlights.map((highlight) => (
              <li
                key={highlight.id}
                className="rounded-lg border border-line bg-surface p-5"
              >
                <p className="text-xs text-ink-muted">{highlight.measure}</p>
                <h3 className="mt-1.5 font-editorial text-xl leading-snug text-ink">
                  <Link
                    href={`/regionen/${highlight.regionId}`}
                    className="hover:text-accent hover:underline underline-offset-4"
                  >
                    {highlight.regionName}
                  </Link>
                </h3>
                <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <ChangeBadge
                    change={highlight.change}
                    metric={highlight.metric}
                    showAbsolute
                  />
                  <span className="text-sm text-ink-muted">
                    {METRIC_LABELS[highlight.metric]} aktuell:{" "}
                    {formatMetric(highlight.level, highlight.metric)}
                  </span>
                </div>
                <div className="mt-4">
                  <WatchButton
                    regionId={highlight.regionId}
                    regionName={highlight.regionName}
                    size="small"
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="einordnung-titel">
        <SectionHeading
          id="einordnung-titel"
          title="Redaktionelle Zusammenfassung"
          description="Getrennt von den Daten ausgewiesen: Diese Einordnung deutet die Zahlen, sie ersetzt sie nicht."
        />
        <EditorialNote insight={getOverviewInsight(period)} />
      </section>

      <section aria-labelledby="niveau-titel">
        <SectionHeading
          id="niveau-titel"
          title="Preisniveau im Vergleich"
          description="Alle Demo-Regionen, gereiht nach aktuellem Angebotspreis je m² beim Kauf."
          aside={<DemoBadge />}
        />
        <div className="mb-3 rounded-lg border border-line bg-surface p-4">
          <ComparisonBars
            entries={ranking.map((entry) => ({
              regionId: entry.regionId,
              label: entry.regionName,
              value: entry.value,
            }))}
            metric="salePricePerSqm"
            period={period}
          />
        </div>

        <div className="table-scroll rounded-lg border border-line bg-surface">
          <table className="w-full min-w-[28rem] border-collapse text-sm">
            <caption className="sr-only">
              Angebotspreis Kauf je Quadratmeter, absteigend gereiht, Stand{" "}
              {formatPeriod(period)}
            </caption>
            <thead>
              <tr className="border-b border-line text-left">
                <th scope="col" className="px-4 py-3 font-medium text-ink-muted">
                  Region
                </th>
                <th scope="col" className="px-4 py-3 font-medium text-ink-muted">
                  Angebotspreis Kauf
                </th>
                <th scope="col" className="px-4 py-3 font-medium text-ink-muted">
                  Stand
                </th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((entry) => (
                <tr
                  key={entry.regionId}
                  className="border-b border-line/60 last:border-0"
                >
                  <th scope="row" className="px-4 py-2.5 text-left font-normal">
                    <Link
                      href={`/regionen/${entry.regionId}`}
                      className="text-ink hover:text-accent hover:underline underline-offset-2"
                    >
                      {entry.regionName}
                    </Link>
                  </th>
                  <td className="px-4 py-2.5 tabular-nums text-ink">
                    {formatSalePerSqm(entry.value)}
                  </td>
                  <td className="px-4 py-2.5 text-ink-muted">
                    {formatPeriod(entry.period)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <AboCta
        title="Beobachte deine Region weiter"
        description="Das Wohnmarkt-Update erscheint monatlich. Mit einer eigenen Beobachtungsliste siehst du beim nächsten Mal sofort, was sich in genau deinen Regionen verändert hat — statt jedes Mal neu zu suchen."
      />

      <DataSourcePanel />
    </div>
  );
}
