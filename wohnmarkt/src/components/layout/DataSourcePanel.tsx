import Link from "next/link";
import { getDataSource } from "@/data";
import { formatDate } from "@/lib/format";

const STATUS_LABEL = {
  demo: "Demo-Daten",
  planned: "Quelle geplant",
  verified: "Verifizierte Daten",
} as const;

/**
 * Ausweis der Datenquelle. Steht auf jeder Seite unter den Inhalten, damit
 * Herkunft und Status der Zahlen nie erst gesucht werden müssen.
 */
export function DataSourcePanel() {
  const source = getDataSource();

  return (
    <section
      aria-labelledby="datenquelle-titel"
      className="rounded-lg border border-line bg-surface p-5"
    >
      <h2
        id="datenquelle-titel"
        className="text-xs font-medium tracking-wide text-ink-muted uppercase"
      >
        Datenquelle
      </h2>
      <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-ink-muted">Quelle</dt>
          <dd className="mt-0.5 text-ink">{source.name}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-muted">Status</dt>
          <dd className="mt-0.5 text-ink">{STATUS_LABEL[source.status]}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-muted">Datenstand</dt>
          <dd className="mt-0.5 text-ink">{formatDate(source.lastUpdated)}</dd>
        </div>
      </dl>
      <p className="mt-3 max-w-prose text-sm leading-relaxed text-ink-soft">
        {source.methodologyNote}
      </p>
      <Link
        href="/methodik"
        className="mt-3 inline-block text-sm font-medium text-accent underline underline-offset-2 hover:text-accent-dark"
      >
        Vollständige Methodik
      </Link>
    </section>
  );
}
