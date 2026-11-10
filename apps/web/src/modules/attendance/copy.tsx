"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import en from "../../../messages/en.json";
import hi from "../../../messages/hi.json";
const Copy = createContext<{
  t: typeof en.attendance;
  lang: "en" | "hi";
  setLang: (lang: "en" | "hi") => void;
}>({ t: en.attendance, lang: "en", setLang: () => {} });
export const useAttendanceCopy = () => useContext(Copy);
const buttonBase = "min-h-11 min-w-11 rounded-xl border px-3 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1F6F6B] disabled:cursor-not-allowed disabled:opacity-50";
const buttonVariants = {
  default: "border-[#D5E3DE] bg-white text-[#1F6F6B]",
  primary: "border-[#1F6F6B] bg-[#1F6F6B] text-white",
  selected: "border-[#1F6F6B] bg-[#D9EEEA] text-[#1F6F6B] ring-1 ring-[#1F6F6B]",
};
export const buttonClass = (variant: keyof typeof buttonVariants = "default") => `${buttonBase} ${buttonVariants[variant]}`;
export const button = buttonClass();
export const field = "min-h-11 w-full rounded-xl border border-[#D5E3DE] bg-white px-3 py-2 text-sm";
export function AttendanceCopyProvider({ children }: {
  children: ReactNode;
}) {
  const [lang, setLang] = useState<"en" | "hi">("en");
  useEffect(() => {
    let alive = true;
    queueMicrotask(() => {
      try {
        const v = localStorage.getItem("parentplus:attendance-language");
        if (alive && (v === "en" || v === "hi"))
          setLang(v);
      }
      catch {
        /* Optional preference. */
      }
    });
    return () => {
      alive = false;
    };
  }, []);
  const t = lang === "hi" ? hi.attendance : en.attendance;
  return <Copy.Provider value={{ t, lang, setLang }}>{children}
  </Copy.Provider>;
}
export function AttendanceLanguageSelect() {
  const { t, lang, setLang } = useAttendanceCopy();
  return <label className="mt-4 block text-xs text-[#5C6B73]">{t.language}<select className={field} aria-label={t.language} value={lang} onChange={e => {
    const v = e.target.value as "en" | "hi";
    setLang(v);
    try {
      localStorage.setItem("parentplus:attendance-language", v);
    }
    catch {
      /* Optional preference. */
    }
  }}>
    <option value="en">English</option>
    <option value="hi">हिन्दी</option>
  </select>
  </label>;
}
