import type { Metadata } from "next";
import { getCurrentPeriod, getRegions } from "@/data";
import { formatPeriod } from "@/lib/format";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { DemoBadge } from "@/components/ui/DemoBadge";
import { RegionCard } from "@/components/region/RegionCard";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";
import { AboCta } from "@/components/premium/AboCta";

export const metadata: Metadata = {
  title: "Regionen",
  description:
    "Alle Regionen des Prototypen mit aktuellem Preisniveau und Veränderung gegenüber dem Vormonat.",
};

export default function RegionenPage() {
  const regions = getRegions();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-editorial text-3xl leading-tight text-ink">Regionen</h1>
        <p className="mt-2 max-w-prose text-base leading-relaxed text-ink-soft">
          {regions.length} Regionen stehen im Prototyp zur Auswahl. Die Auswahl ist
          eine Demo-Zusammenstellung und lässt sich später durch die Regionsschlüssel
          einer echten Datenquelle ersetzen.
        </p>
      </div>

      <section aria-labelledby="regionen-liste">
        <SectionHeading
          id="regionen-liste"
          title={`Übersicht, Stand ${formatPeriod(getCurrentPeriod())}`}
          description="Jede Karte zeigt das aktuelle Niveau und die Veränderung gegenüber der Vorperiode."
          aside={<DemoBadge />}
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {regions.map((region) => (
            <RegionCard key={region.id} region={region} />
          ))}
        </div>
      </section>

      <AboCta />
      <DataSourcePanel />
    </div>
  );
}
