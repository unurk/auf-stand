import type { Metadata } from "next";
import Link from "next/link";
import { getIssues, getRegion } from "@/data";
import { getIssueKeyMetric } from "@/lib/highlights";
import { KEINE_DATEN, formatDate, formatMetric, formatPeriod } from "@/lib/format";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { DemoBadge } from "@/components/ui/DemoBadge";
import { ChangeBadge } from "@/components/ui/ChangeBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";
import { AboCta } from "@/components/premium/AboCta";

export const metadata: Metadata = {
  title: "Archiv",
  description: "Frühere Ausgaben des Presse Wohnmarkt-Updates.",
};

export default function ArchivPage() {
  const issues = getIssues();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-editorial text-3xl leading-tight text-ink">Archiv</h1>
        <p className="mt-2 max-w-prose text-base leading-relaxed text-ink-soft">
          Frühere Ausgaben des Wohnmarkt-Updates. Der Wert des Archivs liegt im
          Verlauf: Erst über mehrere Ausgaben zeigt sich, ob eine Bewegung anhält
          oder ein einzelner Monatsausschlag war.
        </p>
      </div>

      <section aria-labelledby="ausgaben-titel">
        <SectionHeading
          id="ausgaben-titel"
          title="Ausgaben"
          description="Jede Ausgabe nennt eine berechnete Kennzahl aus den Daten der jeweiligen Periode."
          aside={<DemoBadge label="Demo-Ausgaben" />}
        />

        {issues.length === 0 ? (
          <EmptyState
            title="Keine Ausgaben vorhanden"
            description="Im Prototyp sind derzeit keine Ausgaben hinterlegt."
          />
        ) : (
          <ul className="space-y-4">
            {issues.map((issue) => {
              const key = getIssueKeyMetric(issue.period, issue.featuredRegionIds);
              return (
                <li
                  key={issue.id}
                  className="rounded-lg border border-line bg-surface p-5 sm:p-6"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-ink-muted">
                      {formatDate(issue.publicationDate)}
                    </span>
                    {issue.isDemo && <DemoBadge label="Demo-Inhalt" />}
                  </div>
                  <h3 className="mt-1.5 font-editorial text-xl leading-snug text-ink">
                    <Link
                      href={`/archiv/${issue.id}`}
                      className="hover:text-accent hover:underline underline-offset-4"
                    >
                      {issue.title}
                    </Link>
                  </h3>
                  <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
                    {issue.summary}
                  </p>

                  <div className="mt-4 rounded-md bg-paper p-3">
                    <div className="text-xs text-ink-muted">
                      Wichtigste Kennzahl der Ausgabe
                    </div>
                    {key ? (
                      <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
                        <span className="text-ink">
                          {key.regionName}: {formatMetric(key.level, key.metric)}
                        </span>
                        <ChangeBadge change={key.change} metric={key.metric} />
                        <span className="text-xs text-ink-muted">
                          {key.measure}
                        </span>
                      </div>
                    ) : (
                      <div className="mt-1 text-sm text-ink-muted">{KEINE_DATEN}</div>
                    )}
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line pt-3 text-sm">
                    <Link
                      href={`/archiv/${issue.id}`}
                      className="font-medium text-accent underline underline-offset-2 hover:text-accent-dark"
                    >
                      Zur Detailansicht
                    </Link>
                    <span className="text-xs text-ink-muted">
                      Regionen:{" "}
                      {issue.featuredRegionIds
                        .map((id) => getRegion(id)?.name ?? id)
                        .join(", ")}{" "}
                      · Periode {formatPeriod(issue.period)}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <AboCta
        title="Der Verlauf ist der eigentliche Nutzen"
        description="Im Abo bleiben frühere Ausgaben samt Detailanalyse zugänglich — so lässt sich eine aktuelle Bewegung an dem messen, was vorher war."
      />

      <DataSourcePanel />
    </div>
  );
}
