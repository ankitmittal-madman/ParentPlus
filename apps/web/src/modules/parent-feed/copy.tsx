"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import en from "../../../messages/en.json";
import hi from "../../../messages/hi.json";
import { field } from "../attendance/copy";
const Copy = createContext({ t: en.parentFeed, lang: "en" as "en" | "hi", setLang: (() => {}) as (value: "en" | "hi") => void });
export const useParentCopy = () => useContext(Copy);
export function ParentCopyProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<"en" | "hi">("en");
  useEffect(() => { let alive = true; queueMicrotask(() => { try { const stored = localStorage.getItem("parentplus:parent-language"); if (alive && (stored === "en" || stored === "hi")) setLang(stored); } catch {} }); return () => { alive = false; }; }, []);
  return <Copy.Provider value={{ t: lang === "hi" ? hi.parentFeed : en.parentFeed, lang, setLang }}>{children}</Copy.Provider>;
}
export function ParentLanguageSelect() {
  const { t, lang, setLang } = useParentCopy();
  return <label className="block text-xs">{t.language}<select aria-label={t.language} className={`${field} mt-1`} value={lang} onChange={e => { const value = e.target.value as "en" | "hi"; setLang(value); try { localStorage.setItem("parentplus:parent-language", value); } catch {} }}><option value="en">English</option><option value="hi">हिन्दी</option></select></label>;
}
export function parentDate(value: string, lang: string) { return new Intl.DateTimeFormat(lang === "en" ? "en-IN" : "hi-IN", { timeZone: "UTC", day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00Z`)); }
