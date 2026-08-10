import Link from "next/link";
import { getCurrentPeriod, getDataSource } from "@/data";
import { formatDate, formatPeriod } from "@/lib/format";
import { PremiumToggle } from "@/components/premium/PremiumToggle";

export function SiteHeader() {
  const source = getDataSource();

  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6">
        <div>
          <Link href="/" className="inline-block">
            <span className="block text-[11px] font-semibold tracking-[0.18em] text-accent uppercase">
              Die Presse
            </span>
            <span className="mt-0.5 block font-editorial text-2xl leading-tight text-ink sm:text-3xl">
              Wohnmarkt-Update
            </span>
          </Link>
          <p className="mt-1 text-xs text-ink-muted">
            Ausgabe {formatPeriod(getCurrentPeriod())} · Datenstand{" "}
            {formatDate(source.lastUpdated)}
          </p>
        </div>
        <PremiumToggle />
      </div>
    </header>
  );
}
