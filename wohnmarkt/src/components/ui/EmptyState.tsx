import type { ReactNode } from "react";

/** Einheitlicher leerer Zustand — erklärt, statt nur „nichts da“ zu sagen. */
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-line-strong bg-surface p-8 text-center">
      <h3 className="font-editorial text-lg text-ink">{title}</h3>
      <p className="mx-auto mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
        {description}
      </p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
