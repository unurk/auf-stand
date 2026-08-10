/**
 * Kennzeichnet einen Block als synthetische Beispieldaten bzw. als
 * redaktionellen Demo-Text. Wird an jeden Kennzahlen- und Analyseblock gesetzt.
 */
export function DemoBadge({
  label = "Beispieldaten",
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border border-demo/30 bg-demo-bg px-2 py-0.5 text-[11px] font-medium tracking-wide text-demo uppercase ${className}`}
    >
      <span aria-hidden="true">◆</span>
      {label}
    </span>
  );
}
