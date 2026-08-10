import type { Metadata } from "next";
import { getObservationsForRegions, getRegions } from "@/data";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { DemoBadge } from "@/components/ui/DemoBadge";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";
import { PremiumGate } from "@/components/premium/PremiumGate";
import { WatchlistView } from "@/components/region/WatchlistView";

export const metadata: Metadata = {
  title: "Beobachtung",
  description:
    "Persönliche Beobachtungsliste: ausgewählte Regionen mit letzter Veränderung und aktuellem Preisniveau.",
};

export default function BeobachtungPage() {
  const regions = getRegions();
  const seriesByRegion = getObservationsForRegions(
    regions.map((region) => region.id),
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-editorial text-3xl leading-tight text-ink">
          Deine Beobachtung
        </h1>
        <p className="mt-2 max-w-prose text-base leading-relaxed text-ink-soft">
          Hier stehen die Regionen, die du beobachtest — mit der letzten Veränderung
          und dem Datum des jüngsten Updates. Die Liste liegt ausschließlich im
          Speicher dieses Browsers: kein Konto, kein Server, keine personenbezogenen
          Daten.
        </p>
      </div>

      <section aria-labelledby="liste-titel">
        <SectionHeading
          id="liste-titel"
          title="Beobachtete Regionen"
          description="Kennzahlen und Veränderungen werden bei jedem Aufruf neu aus den Daten berechnet."
          aside={<DemoBadge />}
        />
        <PremiumGate
          title="Beobachtungsliste"
          description="Die persönliche Beobachtungsliste ist Teil des Abo-Nutzwerts: mehrere Regionen dauerhaft verfolgen und bei jedem Update sofort die Veränderungen sehen. Schalte die Ansicht um, um sie im Prototyp auszuprobieren."
        >
          <WatchlistView regions={regions} seriesByRegion={seriesByRegion} />
        </PremiumGate>
      </section>

      <DataSourcePanel />
    </div>
  );
}
