"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "presse-wohnmarkt.demo-abo.v1";
const CHANGE_EVENT = "presse-wohnmarkt:premium";

/**
 * SIMULIERTER Abo-Zustand. Nur ein Schalter im localStorage — es gibt keinen
 * Checkout, keine Preise, keine Konten und keine Prüfung gegen ein echtes
 * Abo-System. Der Schalter existiert, damit im Review beide Zustände
 * (frei / Abo) am selben Prototypen vergleichbar sind.
 */
export function usePremium() {
  const [isPremium, setIsPremium] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const read = () => {
      try {
        setIsPremium(window.localStorage.getItem(STORAGE_KEY) === "1");
      } catch {
        setIsPremium(false);
      }
    };
    read();
    setHydrated(true);

    window.addEventListener("storage", read);
    window.addEventListener(CHANGE_EVENT, read);
    return () => {
      window.removeEventListener("storage", read);
      window.removeEventListener(CHANGE_EVENT, read);
    };
  }, []);

  const set = useCallback((next: boolean) => {
    setIsPremium(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    } catch {
      // Storage nicht verfügbar: Zustand gilt nur für diese Session.
    }
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }, []);

  const toggle = useCallback(() => set(!isPremium), [isPremium, set]);

  return { isPremium, hydrated, set, toggle };
}
