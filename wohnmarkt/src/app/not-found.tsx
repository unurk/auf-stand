import Link from "next/link";
import { EmptyState } from "@/components/ui/EmptyState";

export default function NotFound() {
  return (
    <EmptyState
      title="Diese Seite gibt es nicht"
      description="Möglicherweise wurde eine Region entfernt oder umbenannt. Die Übersicht listet alle Regionen des Prototypen."
      action={
        <Link
          href="/regionen"
          className="inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark"
        >
          Zur Regionsübersicht
        </Link>
      }
    />
  );
}
