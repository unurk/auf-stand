# Presse Wohnmarkt-Update — Prototyp

Klickbarer Prototyp für ein wiederkehrendes Abo-Nutzwertprodukt der „Presse“:
Nutzer:innen beobachten, wie sich Angebotspreise, Mieten und das Angebot in
ausgewählten österreichischen Regionen entwickeln.

> **Nicht produktionsreif.** Diese Anwendung arbeitet ausschließlich mit
> **synthetischen Beispieldaten**. Es gibt keine bestätigte Datenpartnerschaft
> und keinen bestätigten Datenzugang. Kein Wert bildet einen realen Markt ab.
> Die Abo-Bereiche sind simuliert: kein Checkout, keine Preise, keine Konten,
> keine personenbezogenen Daten.

Der Prototyp ist ein eigenständiges Nebenprojekt im Repository und hat mit der
Lagebild-Pipeline (`copilot/`, `site/`) nichts zu tun — er teilt keinen Code,
keine Daten und keinen Deploy.

## Starten

Voraussetzung: Node.js 20 oder neuer.

```bash
cd wohnmarkt
npm install
npm run dev          # http://localhost:3000
```

Weitere Skripte:

| Befehl | Zweck |
| --- | --- |
| `npm run build` | Produktionsbuild (prüft zugleich Typen und Lint) |
| `npm run start` | Produktionsbuild lokal ausliefern |
| `npm run typecheck` | TypeScript ohne Emit |
| `npm run lint` | ESLint (next/core-web-vitals) |
| `npm test` | Vitest: Berechnungs- und Formatierungslogik |
| `npm run generate:data` | Beispieldaten neu erzeugen (deterministisch) |

Der Prototyp läuft standardmäßig nur lokal. Er ist bewusst **nicht** an den
bestehenden Pages-/Vercel-Deploy des Repositories angeschlossen — dort liegt das
Lagebild-Produkt, das davon unberührt bleibt.

## Teilbaren Link erzeugen

Für ein Review mit anderen reicht ein Vorschau-Deployment aus diesem Ordner:

```bash
cd wohnmarkt
npx vercel          # beim ersten Mal: Login im Browser, dann Fragen mit Enter bestätigen
```

Die CLI erkennt Next.js selbst und gibt am Ende eine Preview-URL aus. Wichtig
dabei: Aus dem Ordner `wohnmarkt/` deployen, nicht aus dem Repository-Wurzel-
verzeichnis — die dortige `vercel.json` gehört zum Lagebild und würde statt des
Prototypen den Ordner `site/` ausliefern.

### Deploy über die Vercel-Weboberfläche

Alternativ ohne Terminal: Repo auf [vercel.com/new](https://vercel.com/new)
importieren und **Root Directory auf `wohnmarkt`** setzen. Das ist der
entscheidende Schritt — ohne ihn greift die `vercel.json` im
Wurzelverzeichnis, die zum Lagebild gehört und `site/` als Ausgabeverzeichnis
erwartet. Der Build scheitert dann mit:

```
No Output Directory named "site" found after the Build completed.
```

Die `vercel.json` in diesem Ordner setzt Next.js explizit und lässt Build-,
Install- und Ausgabeverzeichnis auf den Vorgaben des Frameworks. Sie hat
Vorrang vor den Einstellungen im Vercel-Dashboard — sobald Root Directory
korrekt auf `wohnmarkt` zeigt, kann die Konfiguration des Lagebilds nicht mehr
hineinwirken.

Vor dem Weitergeben eines Links bedenken: Die Seite trägt Presse-Branding und
zeigt Zahlen, die wie Marktdaten aussehen. Der Demo-Hinweis steht deshalb
dauerhaft im Seitenkopf, an jedem Kennzahlenblock und in der Fußzeile, und die
Seite ist auf `noindex` gesetzt. Diese Hinweise bitte nicht entfernen.

## Technik

- **Next.js 15** (App Router) mit **React 19** und **TypeScript** (strict)
- **Tailwind CSS v4** (CSS-first, Tokens in `src/app/globals.css`)
- **Recharts** für Linien- und Balkendiagramme
- **localStorage** für Beobachtungsliste und simulierten Abo-Zustand
- **Vitest** für die Logiktests
- Keine externen Requests zur Laufzeit — auch keine Webfonts

Serverkomponenten sind der Standard; `"use client"` steht nur dort, wo
Interaktion nötig ist (Charts, Auswahl, Beobachtungsliste, Abo-Schalter).

## Seiten

| Route | Inhalt |
| --- | --- |
| `/` | Aktuelles Update: Kennzahlen, wichtigste Bewegungen, redaktionelle Zusammenfassung, Preisniveau-Reihung |
| `/regionen` | Alle Regionen mit Niveau und Veränderung |
| `/regionen/[regionId]` | Detailseite: Niveau, Zeitreihe, Verhältniswerte, Analyse, „Region beobachten“ |
| `/vergleich` | Regionenvergleich mit Diagramm und Vergleichstabelle |
| `/beobachtung` | Persönliche Beobachtungsliste (localStorage) |
| `/archiv`, `/archiv/[issueId]` | Frühere Ausgaben mit berechneter Kennzahl |
| `/methodik` | Datenquelle, Rechenregeln, Zeiträume, Lücken, Grenzen |
| `/abo` | Gegenüberstellung frei / im Abo (simuliert) |

## Datenmodell

Definiert in `src/data/types.ts`:

- **`Region`** — `id`, `name`, `state`, `type`, `description`
- **`MarketObservation`** — ein Monatswert je Region: `salePricePerSqm`,
  `rentPricePerSqm`, `listingsCount`, `averageSizeSqm`. Jede Kennzahl kann
  `null` sein.
- **`EditorialInsight`** — redaktionelle Einordnung, optional regionsbezogen,
  mit `isDemo`
- **`ReportIssue`** — eine Ausgabe des Updates
- **`DataSourceInfo`** — Name, `status` (`demo` | `planned` | `verified`),
  Datenstand, Methodikhinweis

`src/data/index.ts` ist die **einzige** Zugriffsschicht. Kein Modul außerhalb
von `src/data/` liest die Fixtures direkt.

## Demo-Daten

- **8 Regionen** (`src/data/regions.ts`): Wien Neubau, Wien Donaustadt, Graz,
  Salzburg Stadt, Linz, Innsbruck, St. Pölten, Klagenfurt
- **24 Monatsperioden** (Juli 2024 – Juni 2026), 187 Beobachtungen in
  `src/data/observations.json`, erzeugt von
  `scripts/generate-demo-data.mjs` mit festem Seed (reproduzierbar)
- **3 Demo-Ausgaben** (`src/data/issues.ts`): April, Mai und Juni 2026
- **9 redaktionelle Einordnungen** (`src/data/insights.ts`), alle `isDemo: true`

**Absichtliche Datenlücken**, damit die Fehlwert-Behandlung sichtbar ist:

- *Klagenfurt* — keine Mietwerte in Mai und Juni 2026
- *St. Pölten* — die ersten fünf Perioden fehlen vollständig

Fehlende Werte erscheinen überall als `[Keine Daten verfügbar]`. Sie werden
nicht als 0 gerechnet, nicht interpoliert und nicht aus dem Vormonat
fortgeschrieben; im Diagramm bleibt die Linie unterbrochen.

## Berechnungen

Alle Kennzahlen der Oberfläche entstehen in `src/lib/metrics.ts` und werden in
`src/lib/format.ts` formatiert — **keine Zahl steht als Text in einer
Komponente**. Enthalten sind unter anderem `changeVsPrevious`, `changeVsFirst`,
`averageAcrossRegions`, `rankByLevel`, `rankByChange`, `relativeToAverage`,
`priceToRentRatio` und `compareRegions`. Jede Funktion liefert `null`, wenn
Daten fehlen. `src/lib/highlights.ts` leitet daraus die Dashboard-Bewegungen
und die Kennzahl je Archiv-Ausgabe ab.

Getestet mit `npm test` (26 Tests, Schwerpunkt Fehlwerte und Lücken).

## Anschluss einer echten Datenquelle

Vorbereitet, aber bewusst nicht umgesetzt. Nötig wären genau drei Schritte:

1. **`scripts/generate-demo-data.mjs` ersetzen** — der Abruf der echten Quelle
   schreibt dasselbe Format nach `src/data/observations.json`. Alternativ das
   Lesen in `src/data/index.ts` auf einen API-Aufruf umstellen; die
   Funktionssignaturen dort sind der einzige Berührungspunkt zur übrigen App.
2. **`src/data/source.ts`** — `status` von `"demo"` auf `"verified"` setzen,
   Name und Methodikhinweis anpassen. Banner, Badges und Panels folgen
   automatisch, weil sie den Status auslesen.
3. **`src/data/regions.ts`** — die Demo-Regionen durch die Regionsschlüssel der
   Quelle ersetzen.

Vorher zu klären: Datenzugang, Lizenz- und Veröffentlichungsrechte, konkrete
Datenfelder, Aktualisierungsrhythmus und die Frage, ob Angebots- oder
Transaktionsdaten vorliegen.

## Bekannte Einschränkungen

- Keine echten Marktdaten; keine benannte oder bestätigte Quelle.
- Angebotspreise sind nicht gleich tatsächlich bezahlte Preise.
- Keine Prognosen, keine Qualitäts- oder Ausstattungsbereinigung, keine
  Gewichtung nach Marktgröße.
- Der Abo-Zustand ist ein Schalter im Browserspeicher; die Sperren sind eine
  Darstellung des Nutzwerts, keine Zugriffskontrolle.
- Beobachtungsliste nur auf diesem Gerät, ohne Konto und ohne Synchronisierung;
  sie geht verloren, wenn der Browserspeicher gelöscht wird.
- Ältere Demo-Ausgaben haben bewusst keine eigene redaktionelle Einordnung —
  die aktuelle wird nicht wiederverwendet.
- Keine Tests der React-Komponenten; geprüft sind die Logikmodule.
