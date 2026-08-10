import type { Metadata } from "next";
import Link from "next/link";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { AboCta } from "@/components/premium/AboCta";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";

export const metadata: Metadata = {
  title: "Abo-Nutzwert (simuliert)",
  description:
    "Was im freien Bereich sichtbar ist und was der Abo-Bereich zeigen würde — als Simulation ohne Kauf.",
};

const FREI = [
  {
    title: "Kurze Marktübersicht",
    text: "Die wichtigsten Bewegungen der aktuellen Ausgabe und der Durchschnitt über alle Regionen.",
    href: "/",
  },
  {
    title: "Alle Regionen im Überblick",
    text: "Aktuelles Preisniveau und die Veränderung gegenüber der Vorperiode je Region.",
    href: "/regionen",
  },
  {
    title: "Vergleich von zwei Regionen",
    text: "Zwei Regionen über 6 oder 12 Monate, mit Diagramm und Vergleichstabelle.",
    href: "/vergleich",
  },
  {
    title: "Archivübersicht",
    text: "Titel, Datum, Zusammenfassung und die wichtigste Kennzahl früherer Ausgaben.",
    href: "/archiv",
  },
];

const IM_ABO = [
  {
    title: "Persönliche Beobachtungsliste",
    text: "Mehrere Regionen dauerhaft verfolgen und bei jedem Update sofort sehen, was sich dort verändert hat.",
    href: "/beobachtung",
  },
  {
    title: "Vollständiger Regionenvergleich",
    text: "Bis zu vier Regionen nebeneinander, über den gesamten Zeitraum von 24 Monaten.",
    href: "/vergleich",
  },
  {
    title: "Detaillierte Zeitreihe",
    text: "Die lange Reihe je Region und Kennzahl — für die Unterscheidung zwischen Ausreißer und Trend.",
    href: "/regionen",
  },
  {
    title: "Archiv mit vertiefter Analyse",
    text: "Frühere Ausgaben inklusive Kennzahlen der jeweiligen Periode und redaktioneller Einordnung.",
    href: "/archiv",
  },
];

export default function AboPage() {
  return (
    <div className="space-y-10">
      <div>
        <h1 className="font-editorial text-3xl leading-tight text-ink">
          Was das Abo zeigen würde
        </h1>
        <p className="mt-2 max-w-prose text-base leading-relaxed text-ink-soft">
          Diese Seite stellt gegenüber, was im Prototyp frei zugänglich ist und was
          hinter dem simulierten Abo-Bereich liegt. Sie dient dazu, den
          wiederkehrenden Nutzwert zu beurteilen — nicht dazu, ein Produkt zu
          verkaufen.
        </p>
      </div>

      <section
        aria-labelledby="hinweis-titel"
        className="rounded-lg border border-line bg-surface p-5"
      >
        <h2 id="hinweis-titel" className="font-medium text-ink">
          Simulation ohne Kauf
        </h2>
        <p className="mt-1.5 max-w-prose text-sm leading-relaxed text-ink-soft">
          Es gibt keinen Bestellvorgang, keine Zahlungsabwicklung, kein Konto und
          keine Preise. Über die Abo-Ansicht schaltet allein ein Wert im
          Browserspeicher um, damit beide Zustände am selben Prototypen vergleichbar
          sind. Preise, Laufzeiten und Leistungsumfang eines echten Produkts sind
          nicht entschieden und werden hier deshalb auch nicht angedeutet.
        </p>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="frei-titel">
          <SectionHeading id="frei-titel" title="Frei zugänglich" />
          <ul className="space-y-3">
            {FREI.map((item) => (
              <li
                key={item.title}
                className="rounded-lg border border-line bg-surface p-4"
              >
                <h3 className="font-editorial text-base text-ink">
                  <Link
                    href={item.href}
                    className="hover:text-accent hover:underline underline-offset-4"
                  >
                    {item.title}
                  </Link>
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                  {item.text}
                </p>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="abo-titel">
          <SectionHeading id="abo-titel" title="Im Abo simuliert" />
          <ul className="space-y-3">
            {IM_ABO.map((item) => (
              <li
                key={item.title}
                className="rounded-lg border border-accent/25 bg-accent/[0.04] p-4"
              >
                <h3 className="font-editorial text-base text-ink">
                  <Link
                    href={item.href}
                    className="hover:text-accent hover:underline underline-offset-4"
                  >
                    {item.title}
                  </Link>
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                  {item.text}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <AboCta />
      <DataSourcePanel />
    </div>
  );
}
