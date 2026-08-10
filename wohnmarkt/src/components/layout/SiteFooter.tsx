import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-12 border-t border-line bg-surface">
      <div className="mx-auto max-w-5xl px-4 py-8 text-sm text-ink-muted sm:px-6">
        <p className="max-w-prose leading-relaxed">
          <strong className="font-medium text-ink-soft">
            Prototyp, nicht produktionsreif.
          </strong>{" "}
          Diese Anwendung verwendet ausschließlich synthetische Beispieldaten.
          Eine Datenpartnerschaft und die Veröffentlichung konkreter Marktdaten
          sind nicht vereinbart. Es gibt keinen Kaufabschluss, keine Konten und
          keine personenbezogene Verarbeitung; die Beobachtungsliste liegt allein
          im Browser dieses Geräts.
        </p>
        <nav aria-label="Fußzeile" className="mt-4 flex flex-wrap gap-x-5 gap-y-2">
          <Link href="/methodik" className="underline underline-offset-2 hover:text-ink">
            Methodik
          </Link>
          <Link href="/abo" className="underline underline-offset-2 hover:text-ink">
            Was das Abo zeigen würde
          </Link>
          <Link href="/archiv" className="underline underline-offset-2 hover:text-ink">
            Archiv
          </Link>
        </nav>
      </div>
    </footer>
  );
}
