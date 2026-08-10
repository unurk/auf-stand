import type { Metadata } from "next";
import { getObservationsForRegions, getRegions } from "@/data";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { DemoBadge } from "@/components/ui/DemoBadge";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";
import { RegionComparison } from "@/components/region/RegionComparison";

export const metadata: Metadata = {
  title: "Regionenvergleich",
  description:
    "Zwei oder mehr Regionen über 6, 12 oder 24 Monate vergleichen — Preis, Miete, Angebot und Wohnungsgröße.",
};

export default function VergleichPage() {
  const regions = getRegions();
  const seriesByRegion = getObservationsForRegions(
    regions.map((region) => region.id),
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-editorial text-3xl leading-tight text-ink">
          Regionenvergleich
        </h1>
        <p className="mt-2 max-w-prose text-base leading-relaxed text-ink-soft">
          Stelle Regionen nebeneinander und sieh, ob sie sich gleich oder
          gegenläufig entwickeln. Unterschiede im Quadratmeterpreis lassen sich
          teilweise mit der durchschnittlichen Wohnungsgröße erklären — deshalb
          steht sie gleichrangig neben dem Preis.
        </p>
      </div>

      <section aria-labelledby="vergleich-titel">
        <SectionHeading
          id="vergleich-titel"
          title="Auswahl und Kennzahl"
          description="Alle Werte werden aus derselben Datenbasis berechnet wie die Regionsseiten."
          aside={<DemoBadge />}
        />
        <RegionComparison regions={regions} seriesByRegion={seriesByRegion} />
      </section>

      <DataSourcePanel />
    </div>
  );
}
