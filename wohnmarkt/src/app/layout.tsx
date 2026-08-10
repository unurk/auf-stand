import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { SiteNav } from "@/components/layout/SiteNav";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { DemoBanner } from "@/components/layout/DemoBanner";

export const metadata: Metadata = {
  title: {
    default: "Presse Wohnmarkt-Update (Prototyp)",
    template: "%s · Presse Wohnmarkt-Update",
  },
  description:
    "Prototyp mit synthetischen Beispieldaten: Beobachte, wie sich Preise und Angebot in ausgewählten österreichischen Regionen verändern.",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de-AT">
      <body className="min-h-screen">
        <a
          href="#inhalt"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-accent focus:px-4 focus:py-2 focus:text-white"
        >
          Zum Inhalt springen
        </a>
        <DemoBanner />
        <SiteHeader />
        <SiteNav />
        <main id="inhalt" className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
