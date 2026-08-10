"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Update" },
  { href: "/regionen", label: "Regionen" },
  { href: "/vergleich", label: "Vergleich" },
  { href: "/beobachtung", label: "Beobachtung" },
  { href: "/archiv", label: "Archiv" },
  { href: "/methodik", label: "Methodik" },
];

export function SiteNav() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <nav aria-label="Hauptnavigation" className="border-b border-line bg-surface">
      <ul className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-2 sm:px-4">
        {LINKS.map((link) => {
          const active = isActive(link.href);
          return (
            <li key={link.href} className="shrink-0">
              <Link
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`inline-block border-b-2 px-3 py-3 text-sm whitespace-nowrap transition-colors ${
                  active
                    ? "border-accent font-medium text-accent"
                    : "border-transparent text-ink-soft hover:border-line-strong hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
