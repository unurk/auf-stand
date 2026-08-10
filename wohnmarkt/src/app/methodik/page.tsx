import type { Metadata } from "next";
import Link from "next/link";
import { getDataSource, getObservations, getRegions, periods } from "@/data";
import { formatDate, formatPeriod } from "@/lib/format";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { DataSourcePanel } from "@/components/layout/DataSourcePanel";

export const metadata: Metadata = {
  title: "Methodik",
  description:
    "Datenquelle, Berechnungsregeln, Zeiträume und Einschränkungen des Prototypen.",
};

export default function MethodikPage() {
  const source = getDataSource();
  const regions = getRegions();

  // Lücken direkt aus den Daten ermitteln, statt sie hier aufzuzählen.
  const gaps = regions
    .map((region) => {
      const series = getObservations(region.id);
      const missingPeriods = periods.filter(
        (period) => !series.some((observation) => observation.period === period),
      );
      const missingFields = new Set<string>();
      for (const observation of series) {
        if (observation.salePricePerSqm === null) missingFields.add("Angebotspreis Kauf");
        if (observation.rentPricePerSqm === null) missingFields.add("Angebotsmiete");
        if (observation.listingsCount === null) missingFields.add("Inserate");
        if (observation.averageSizeSqm === null) missingFields.add("Ø Wohnungsgröße");
      }
      return { region, missingPeriods, missingFields: [...missingFields] };
    })
    .filter((entry) => entry.missingPeriods.length > 0 || entry.missingFields.length > 0);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="font-editorial text-3xl leading-tight text-ink">Methodik</h1>
        <p className="mt-2 max-w-prose text-base leading-relaxed text-ink-soft">
          Diese Seite beschreibt, woher die Zahlen dieses Prototypen kommen, wie sie
          berechnet werden und was sie ausdrücklich nicht aussagen.
        </p>
      </div>

      <section
        aria-labelledby="hinweis-titel"
        className="rounded-lg border border-demo/30 bg-demo-bg p-5 sm:p-6"
      >
        <h2 id="hinweis-titel" className="font-editorial text-xl text-ink">
          Prototyp-Hinweis
        </h2>
        <p className="mt-2 max-w-prose text-base leading-relaxed text-ink-soft">
          Diese Anwendung verwendet derzeit synthetische Beispieldaten. Eine spätere
          Datenpartnerschaft und die Veröffentlichung konkreter Marktdaten sind noch
          nicht final vereinbart. Kein Wert auf diesen Seiten bildet einen realen
          Markt ab, und keine Zahl darf als Entscheidungsgrundlage verwendet werden.
        </p>
      </section>

      <section aria-labelledby="quelle-titel">
        <SectionHeading
          id="quelle-titel"
          title="Datenquelle"
          description="Status und Herkunft der Werte."
        />
        <div className="space-y-3 rounded-lg border border-line bg-surface p-5 text-base leading-relaxed text-ink-soft">
          <p>
            <strong className="font-medium text-ink">Aktuell:</strong> {source.name}.
            Die Werte werden von einem Generator im Repository deterministisch
            erzeugt (<code className="text-sm">scripts/generate-demo-data.mjs</code>),
            damit sie über Aufrufe hinweg stabil bleiben. Datenstand der Demo:{" "}
            {formatDate(source.lastUpdated)}.
          </p>
          <p>
            <strong className="font-medium text-ink">Später:</strong> Die produktive
            Datenquelle ist <strong>[ZU PRÜFEN]</strong>. Weder Datenzugang noch
            Lizenzrechte noch die konkret verfügbaren Datenfelder sind geklärt. Bis
            dahin wird keine Quelle namentlich als Partner dargestellt.
          </p>
          <p>
            <strong className="font-medium text-ink">Wichtig:</strong> Angebotspreise
            sind nicht dasselbe wie tatsächlich bezahlte Preise. Sie zeigen, zu
            welchem Preis inseriert wird — nicht, wozu es am Ende zum Abschluss kam.
            Verhandlungsergebnisse, nicht inserierte Objekte und Direktverkäufe
            fehlen darin systematisch.
          </p>
        </div>
      </section>

      <section aria-labelledby="rechnung-titel">
        <SectionHeading
          id="rechnung-titel"
          title="Wie gerechnet wird"
          description="Alle Kennzahlen der Oberfläche entstehen aus diesen Regeln — keine Zahl ist im Text hinterlegt."
        />
        <dl className="space-y-4 rounded-lg border border-line bg-surface p-5 text-base leading-relaxed">
          <div>
            <dt className="font-medium text-ink">Veränderung gegenüber der Vorperiode</dt>
            <dd className="mt-1 text-ink-soft">
              (Wert der jüngsten Periode − Wert der davorliegenden Periode) geteilt
              durch den früheren Wert. Fehlt eine Periode, wird die nächste
              verfügbare davor verwendet; verglichen werden also stets die beiden
              jüngsten Perioden <em>mit</em> Wert.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-ink">Veränderung über den Zeitraum</dt>
            <dd className="mt-1 text-ink-soft">
              Wie oben, aber gegen die erste verfügbare Periode des gewählten
              Zeitfensters. Die Bezugsperiode wird jeweils mit ausgewiesen.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-ink">Durchschnitt über Regionen</dt>
            <dd className="mt-1 text-ink-soft">
              Ungewichtetes Mittel über alle Regionen mit vorhandenem Wert. Regionen
              ohne Wert gehen nicht als Null ein, sondern bleiben unberücksichtigt.
              Der Durchschnitt ist damit nicht nach Marktgröße gewichtet.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-ink">Reihungen</dt>
            <dd className="mt-1 text-ink-soft">
              Sortierung nach aktuellem Niveau oder nach prozentualer Veränderung.
              Reihungen sind deskriptiv: „höchster Angebotspreis je m²“ ist eine
              Messung, keine Bewertung. Aussagen wie „beste Kaufchance“ oder
              „günstigste Region“ werden bewusst nicht getroffen.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-ink">Kaufpreisfaktor</dt>
            <dd className="mt-1 text-ink-soft">
              Angebotspreis je m² geteilt durch die Jahresmiete je m² (Monatsmiete
              mal zwölf). Nebenkosten, Instandhaltung, Leerstand und Steuern sind
              nicht enthalten — der Wert ist ein Verhältnis, keine Rendite.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="zeitraum-titel">
        <SectionHeading
          id="zeitraum-titel"
          title="Verglichene Zeiträume"
          description="Welche Perioden im Datensatz vorliegen und was auswählbar ist."
        />
        <div className="space-y-2 rounded-lg border border-line bg-surface p-5 text-base leading-relaxed text-ink-soft">
          <p>
            Der Datensatz umfasst {periods.length} Monatsperioden von{" "}
            {formatPeriod(periods[0])} bis {formatPeriod(periods[periods.length - 1])}.
            Auswählbar sind Fenster von 6, 12 und 24 Monaten; die Angabe bezieht sich
            immer auf die jüngsten n Perioden.
          </p>
          <p>
            Monatswerte kleiner Märkte schwanken stärker, weil einzelne Objekte den
            Durchschnitt bewegen. Für die Einordnung ist das längere Fenster
            belastbarer als der Einzelmonat.
          </p>
        </div>
      </section>

      <section aria-labelledby="luecken-titel">
        <SectionHeading
          id="luecken-titel"
          title="Fehlende Daten"
          description="Direkt aus dem Datensatz ermittelt, nicht händisch gepflegt."
        />
        <div className="rounded-lg border border-line bg-surface p-5 text-base leading-relaxed text-ink-soft">
          <p>
            Fehlende Werte werden als{" "}
            <code className="text-sm">[Keine Daten verfügbar]</code> ausgewiesen. Sie
            werden nicht als Null gerechnet, nicht interpoliert und nicht aus dem
            Vormonat fortgeschrieben — im Diagramm bleibt die Linie unterbrochen.
          </p>
          {gaps.length > 0 ? (
            <ul className="mt-3 space-y-2 text-sm">
              {gaps.map((entry) => (
                <li key={entry.region.id}>
                  <Link
                    href={`/regionen/${entry.region.id}`}
                    className="font-medium text-accent underline underline-offset-2"
                  >
                    {entry.region.name}
                  </Link>
                  :{" "}
                  {entry.missingPeriods.length > 0 && (
                    <>
                      {entry.missingPeriods.length} Perioden ohne Erhebung (
                      {formatPeriod(entry.missingPeriods[0])} bis{" "}
                      {formatPeriod(entry.missingPeriods[entry.missingPeriods.length - 1])})
                      {entry.missingFields.length > 0 && "; "}
                    </>
                  )}
                  {entry.missingFields.length > 0 && (
                    <>einzelne Perioden ohne {entry.missingFields.join(", ")}</>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm">Der Datensatz weist derzeit keine Lücken auf.</p>
          )}
        </div>
      </section>

      <section aria-labelledby="trennung-titel">
        <SectionHeading
          id="trennung-titel"
          title="Daten und Redaktion getrennt"
          description="Warum beides in der Oberfläche unterschiedlich aussieht."
        />
        <div className="space-y-2 rounded-lg border border-line bg-surface p-5 text-base leading-relaxed text-ink-soft">
          <p>
            Datenblöcke zeigen ausschließlich berechnete Werte. Redaktionelle
            Einordnungen stehen in eigenen, farblich abgesetzten Flächen und sind als
            solche gekennzeichnet — im Prototyp zusätzlich als Demo-Text, weil sie
            Platzhalter sind.
          </p>
          <p>
            Die Einordnungen enthalten bewusst keine konkreten Zahlen: So können Text
            und Daten nicht auseinanderlaufen, wenn sich der Datenstand ändert.
          </p>
        </div>
      </section>

      <section aria-labelledby="grenzen-titel">
        <SectionHeading
          id="grenzen-titel"
          title="Was dieser Prototyp nicht kann"
          description="Bekannte Grenzen, die vor einem Piloten zu klären sind."
        />
        <ul className="list-disc space-y-2 rounded-lg border border-line bg-surface p-5 pl-9 text-base leading-relaxed text-ink-soft">
          <li>Keine echten Marktdaten und keine bestätigte Datenquelle.</li>
          <li>
            Keine Prognosen. Der Prototyp beschreibt Vergangenes und schreibt nichts
            fort.
          </li>
          <li>
            Keine Qualitäts- oder Ausstattungsbereinigung: Unterschiede in Zustand,
            Lage innerhalb der Region und Ausstattung sind in den Werten nicht
            herausgerechnet.
          </li>
          <li>
            Keine Gewichtung nach Marktgröße — eine kleine und eine große Region
            zählen im Durchschnitt gleich viel.
          </li>
          <li>
            Kein Konto und keine Synchronisierung: Die Beobachtungsliste liegt im
            Browser dieses Geräts und geht verloren, wenn der Speicher gelöscht wird.
          </li>
          <li>
            Die Abo-Bereiche sind simuliert. Es gibt keinen Kaufabschluss, keine
            Preise und keine Vertragsbedingungen.
          </li>
        </ul>
      </section>

      <DataSourcePanel />
    </div>
  );
}
