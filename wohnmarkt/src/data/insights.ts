import type { EditorialInsight } from "./types";

/**
 * Redaktionelle Einordnungen. Sie sind im Prototyp Platzhaltertexte
 * (isDemo: true) und werden in der UI immer sichtbar von den Datenblöcken
 * getrennt dargestellt — Daten und Deutung dürfen nicht ineinanderlaufen.
 *
 * Die Texte enthalten bewusst keine konkreten Zahlen: Kennzahlen kommen
 * ausschließlich aus den Daten (src/lib/metrics.ts), damit Text und Daten
 * nicht auseinanderdriften können.
 */
export const insights: EditorialInsight[] = [
  {
    id: "overview-2026-06",
    period: "2026-06",
    title: "Was sich im Juni verändert hat",
    summary:
      "Mieten und Kaufpreise entwickeln sich in den Demo-Regionen unterschiedlich schnell — und das Angebot verschiebt sich vom teuren Zentrum in Richtung Umland.",
    body: "Auffällig ist im Prototyp-Datensatz weniger die Höhe der Preise als deren unterschiedliches Tempo: Die Angebotsmieten legen in allen Regionen stärker zu als die Kaufpreise. Gleichzeitig geht die Zahl der Inserate dort zurück, wo das Preisniveau ohnehin am höchsten ist, während sie im gut angebundenen Umland wächst. Für Beobachter:innen ist das die interessantere Bewegung: Ein schrumpfendes Angebot bei stabilen Preisen bedeutet etwas anderes als fallende Preise bei wachsendem Angebot. Welche der beiden Entwicklungen anhält, lässt sich aus einem einzelnen Monat nicht ableiten — dafür ist die wiederkehrende Beobachtung gedacht.",
    isDemo: true,
  },
  {
    id: "wien-neubau-2026-06",
    regionId: "wien-neubau",
    period: "2026-06",
    title: "Kleines Angebot, träges Preisbild",
    summary:
      "Der Bezirk zeigt im Datensatz das typische Muster eines dichten Altbaugebiets: wenig Bewegung beim Preis, spürbar weniger Inserate.",
    body: "Innerstädtische Altbaubezirke reagieren träge, weil kaum neu gebaut wird und der Bestand selten den Eigentümer wechselt. In den Beispieldaten schlägt sich das in einem hohen, aber wenig dynamischen Kaufpreisniveau nieder, während die Angebotsmieten deutlich schneller steigen. Wer hier vergleicht, sollte die Inseratszahl im Blick behalten: Bei kleinen Fallzahlen bewegt schon eine Handvoll besonders teurer oder besonders günstiger Objekte den Durchschnitt.",
    isDemo: true,
  },
  {
    id: "wien-donaustadt-2026-06",
    regionId: "wien-donaustadt",
    period: "2026-06",
    title: "Neubau hält das Angebot breit",
    summary:
      "Ein wachsender Bestand hält die Inseratszahl hoch — das Preisniveau bleibt im Vergleich zu den Innenbezirken moderat.",
    body: "Flächenbezirke mit laufender Neubautätigkeit haben ein strukturell größeres Angebot, und größere Wohnungen prägen den Schnitt. Im Datensatz führt das zu einer vergleichsweise stabilen Inseratszahl. Für den Vergleich mit Innenbezirken heißt das: Ein Teil des Preisunterschieds ist Lage, ein Teil aber schlicht Wohnungstyp und -größe. Der Quadratmeterpreis gleicht das nur teilweise aus.",
    isDemo: true,
  },
  {
    id: "graz-2026-06",
    regionId: "graz",
    period: "2026-06",
    title: "Universitätsstandort mit Nachfrage nach kleinen Einheiten",
    summary:
      "Die durchschnittliche Wohnungsgröße liegt unter jener der Flächengemeinden — ein Hinweis auf das Gewicht kleiner Einheiten.",
    body: "Studierende und Einpersonenhaushalte verschieben die Nachfrage zu kleinen Wohnungen, und kleine Wohnungen sind je Quadratmeter fast überall teurer als große. Beim Vergleich zweier Regionen lohnt deshalb der Blick auf die durchschnittliche Wohnungsgröße: Unterschiede im Quadratmeterpreis lassen sich teilweise damit erklären und nicht allein mit dem Standort.",
    isDemo: true,
  },
  {
    id: "salzburg-stadt-2026-06",
    regionId: "salzburg-stadt",
    period: "2026-06",
    title: "Knappe Fläche, knappes Angebot",
    summary:
      "Hohes Preisniveau bei rückläufiger Inseratszahl — im Datensatz die deutlichste Angebotsverknappung.",
    body: "Wo die Siedlungsfläche baulich begrenzt ist, wirkt zusätzliche Nachfrage stärker auf den Preis als auf die Menge. Die Beispieldaten bilden das als Kombination aus hohem Niveau und sinkender Inseratszahl ab. Vorsicht bei der Interpretation: Eine sinkende Zahl an Inseraten kann Knappheit bedeuten — oder nur, dass Objekte anders vermarktet werden. Aus Angebotsdaten allein ist das nicht zu unterscheiden.",
    isDemo: true,
  },
  {
    id: "linz-2026-06",
    regionId: "linz",
    period: "2026-06",
    title: "Breiter Bestand dämpft die Ausschläge",
    summary:
      "Kaufpreise bewegen sich im Datensatz kaum, die Mieten steigen langsamer als in den westlichen Landeshauptstädten.",
    body: "Ein großer und vielfältiger Wohnungsbestand samt aktivem gemeinnützigem Sektor dämpft Ausschläge nach oben wie nach unten. In den Beispieldaten zeigt sich das als vergleichsweise flache Kurve. Für die Beobachtung über mehrere Monate ist gerade das nützlich: Regionen mit ruhigem Verlauf eignen sich als Referenz, an der sich Bewegungen anderswo besser einordnen lassen.",
    isDemo: true,
  },
  {
    id: "innsbruck-2026-06",
    regionId: "innsbruck",
    period: "2026-06",
    title: "Enger Markt mit kleinen Fallzahlen",
    summary:
      "Hohes Niveau bei wenigen Inseraten — Monatswerte schwanken hier stärker als in großen Märkten.",
    body: "Je kleiner die Zahl der Inserate, desto größer der Einfluss einzelner Objekte auf den Durchschnitt. Bei Regionen dieser Größenordnung sind einzelne Monatssprünge deshalb mit Vorsicht zu lesen; aussagekräftiger ist der Verlauf über zwölf oder mehr Monate. Der Prototyp stellt die Inseratszahl auch deswegen gleichrangig neben den Preis.",
    isDemo: true,
  },
  {
    id: "st-poelten-2026-06",
    regionId: "st-poelten",
    period: "2026-06",
    title: "Umland mit Aufholbewegung",
    summary:
      "Im Datensatz die stärkste relative Zunahme bei Preisen und Angebot — ausgehend vom niedrigsten Niveau.",
    body: "Standorte mit guter Bahnanbindung profitieren, wenn in der Kernstadt Fläche knapp und teuer wird. In den Beispieldaten steigen hier sowohl die Preise als auch die Inseratszahl. Wichtig für die Einordnung: Eine hohe prozentuale Veränderung von einem niedrigen Ausgangswert ist in absoluten Euro oft weniger, als die Prozentzahl vermuten lässt. Der Prototyp weist deshalb beides aus. Für diese Region beginnt die Erhebung im Datensatz erst später — die ersten Monate fehlen bewusst.",
    isDemo: true,
  },
  {
    id: "klagenfurt-2026-06",
    regionId: "klagenfurt",
    period: "2026-06",
    title: "Kleiner Markt mit Datenlücke",
    summary:
      "Für die jüngsten Monate liegen keine Mietwerte vor — der Prototyp weist das offen aus, statt zu schätzen.",
    body: "Bei kleinen Märkten fallen einzelne Kennzahlen immer wieder unter eine sinnvolle Auswertungsschwelle. Diese Region zeigt im Prototyp genau diesen Fall: Die Mietwerte der jüngsten Perioden fehlen und werden als „[Keine Daten verfügbar]“ ausgewiesen, nicht als Null und nicht als Fortschreibung des Vormonats. Das ist Absicht — eine geschätzte Zahl wäre in einem Datenprodukt schlechter als eine ehrliche Lücke.",
    isDemo: true,
  },
];
