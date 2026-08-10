import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getInsightForRegion,
  getIssue,
  getIssues,
  getObservations,
  getRegion,
} from "@/data";
import { changeVsPrevious, latestWithValue, metricValue } from "@/lib/metrics";
import { getIssueKeyMetric } from "@/lib/highlights";
import {
  formatCount,
  formatDate,
  formatMetric,
  formatPeriod,
  formatRentPerSqm,
  formatSalePerSqm,
} from "@/lib/format";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { MetricTile } from "@/components/ui/MetricTile";
import { ChangeBadge } from "@/components/ui/ChangeBadge";
import { DemoBadge } from "@/components/ui/DemoBadge";
import { EditorialNote } from "@/components/ui/EditorialNote";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";
import { PremiumGate } from "@/components/premium/PremiumGate";

export function generateStaticParams() {
  return getIssues().map((issue) => ({ issueId: issue.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ issueId: string }>;
}): Promise<Metadata> {
  const { issueId } = await params;
  const issue = getIssue(issueId);
  if (!issue) return { title: "Ausgabe nicht gefunden" };
  return { title: issue.title, description: issue.summary };
}

export default async function ArchivDetailPage({
  params,
}: {
  params: Promise<{ issueId: string }>;
}) {
  const { issueId } = await params;
  const issue = getIssue(issueId);
  if (!issue) notFound();

  const key = getIssueKeyMetric(issue.period, issue.featuredRegionIds);

  return (
    <div className="space-y-10">
      <nav aria-label="Brotkrumen" className="text-sm text-ink-muted">
        <Link href="/archiv" className="underline underline-offset-2 hover:text-ink">
          Archiv
        </Link>
        <span aria-hidden="true"> › </span>
        <span className="text-ink">{issue.title}</span>
      </nav>

      <header>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium tracking-wide text-accent uppercase">
            Ausgabe {formatPeriod(issue.period)}
          </span>
          {issue.isDemo && <DemoBadge label="Demo-Inhalt" />}
        </div>
        <h1 className="mt-2 font-editorial text-3xl leading-tight text-ink sm:text-4xl">
          {issue.title}
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Veröffentlicht am {formatDate(issue.publicationDate)}
        </p>
        <p className="mt-4 max-w-prose font-editorial text-lg leading-relaxed text-ink-soft">
          {issue.summary}
        </p>
      </header>

      {key && (
        <section aria-labelledby="kennzahl-titel">
          <SectionHeading
            id="kennzahl-titel"
            title="Wichtigste Kennzahl"
            description={key.measure}
            aside={<DemoBadge />}
          />
          <MetricTile
            label={key.regionName}
            value={formatMetric(key.level, key.metric)}
            change={<ChangeBadge change={key.change} metric={key.metric} showAbsolute />}
            note={`Stand ${formatPeriod(issue.period)}`}
          />
        </section>
      )}

      <section aria-labelledby="regionen-titel">
        <SectionHeading
          id="regionen-titel"
          title="Regionen dieser Ausgabe"
          description="Die Kennzahlen entsprechen dem Stand der jeweiligen Periode."
          aside={<DemoBadge />}
        />
        <PremiumGate
          title="Vertiefte Analyse früherer Ausgaben"
          description="Die vollständigen Kennzahlen und die redaktionelle Analyse früherer Ausgaben gehören zum simulierten Abo-Bereich. In der freien Ansicht bleiben Titel, Datum und Zusammenfassung sichtbar."
        >
          <div className="space-y-6">
            {issue.featuredRegionIds.map((regionId) => {
              const region = getRegion(regionId);
              if (!region) {
                return (
                  <p key={regionId} className="text-sm text-ink-muted">
                    Region „{regionId}“ ist im Datensatz nicht vorhanden.
                  </p>
                );
              }

              const series = getObservations(regionId).filter(
                (observation) => observation.period <= issue.period,
              );
              const sale = metricValue(
                latestWithValue(series, "salePricePerSqm"),
                "salePricePerSqm",
              );
              const rent = metricValue(
                latestWithValue(series, "rentPricePerSqm"),
                "rentPricePerSqm",
              );
              const listings = metricValue(
                latestWithValue(series, "listingsCount"),
                "listingsCount",
              );

              return (
                <div key={regionId} className="space-y-3">
                  <h3 className="font-editorial text-xl leading-snug text-ink">
                    <Link
                      href={`/regionen/${regionId}`}
                      className="hover:text-accent hover:underline underline-offset-4"
                    >
                      {region.name}
                    </Link>
                  </h3>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <MetricTile
                      label="Angebotspreis Kauf"
                      value={formatSalePerSqm(sale)}
                      change={
                        <ChangeBadge
                          change={changeVsPrevious(series, "salePricePerSqm")}
                          metric="salePricePerSqm"
                        />
                      }
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
                    />
                  </div>
                  {/* Einordnung der jeweiligen Periode — für ältere Demo-Ausgaben
                      ist bewusst keine hinterlegt, statt die aktuelle zu recyceln. */}
                  <EditorialNote
                    insight={getInsightForRegion(regionId, issue.period)}
                    variant="summary"
                  />
                </div>
              );
            })}
          </div>
        </PremiumGate>
      </section>

      <DataSourcePanel />
    </div>
  );
}
