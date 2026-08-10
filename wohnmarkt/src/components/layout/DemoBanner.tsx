import Link from "next/link";
import { getDataSource } from "@/data";

/**
 * Dauerhaft sichtbarer Hinweis im Seitenkopf. Der Text richtet sich nach
 * DataSourceInfo.status — er ist nicht hart in die UI geschrieben und ändert
 * sich automatisch, sobald eine echte Quelle angebunden wird.
 */
export function DemoBanner() {
  const source = getDataSource();

  const text =
    source.status === "demo"
      ? "Prototyp mit synthetischen Beispieldaten — keine echten Marktdaten, keine bestätigte Datenquelle."
      : source.status === "planned"
        ? "Datenquelle vereinbart, Anbindung noch offen — die gezeigten Werte sind vorläufig."
        : "Verifizierte Daten.";

  return (
    <div className="border-b border-demo/25 bg-demo-bg">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-2 gap-y-1 px-4 py-2 text-xs text-demo sm:px-6">
        <span aria-hidden="true">◆</span>
        <span>{text}</span>
        <Link
          href="/methodik"
          className="font-medium underline underline-offset-2 hover:text-ink"
        >
          Methodik ansehen
        </Link>
      </div>
    </div>
  );
}
