import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  /*
   * Statischer Export nach wohnmarkt/site/.
   *
   * Der Prototyp braucht keinen Server: Alle Seiten sind vorgerendert, die
   * Interaktion (Auswahl, Diagramme, Beobachtungsliste) läuft im Browser.
   *
   * Der Ordnername ist nicht frei gewählt. Die vercel.json im Wurzelverzeichnis
   * des Repositories gehört zum Lagebild und schreibt `outputDirectory: "site"`
   * fest; Vercel wendet sie auch auf dieses Projekt an. Mit demselben Namen
   * passt der Build unter beiden Konfigurationen — der des Lagebilds wie der
   * eigenen in wohnmarkt/vercel.json.
   *
   * trailingSlash sorgt für Ordner mit index.html statt lose .html-Dateien,
   * damit die Adressen auf beliebigem statischem Hosting sauber auflösen.
   */
  output: "export",
  distDir: "site",
  trailingSlash: true,
};

export default nextConfig;
