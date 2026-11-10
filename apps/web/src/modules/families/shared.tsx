"use client";
import { useEffect, useRef, useState } from "react";
import { observeSessionChanges } from "@/lib/auth/session-observer";
import en from "../../../messages/en.json";
import hi from "../../../messages/hi.json";

export const button =
  "mt-3 rounded-xl bg-[#1F6F6B] px-4 py-3 text-sm font-semibold text-white disabled:opacity-50";
export const field =
  "mt-1 block w-full rounded-xl border border-[#D4DAD5] bg-white p-3 text-sm";
export const card = "mt-5 rounded-2xl bg-white p-5 shadow-sm";
export function useCopy() {
  const [lang, setLang] = useState<"en" | "hi">("en");
  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      try {
        const saved = localStorage.getItem("parentplus:family-language");
        if (active && (saved === "en" || saved === "hi")) setLang(saved);
      } catch {
        /* Language selection remains usable without storage. */
      }
    });
    return () => {
      active = false;
    };
  }, []);
  const choose = (value: "en" | "hi") => {
    setLang(value);
    try {
      localStorage.setItem("parentplus:family-language", value);
    } catch {
      /* Optional preference only. */
    }
  };
  return {
    t: lang === "hi" ? hi.families : en.families,
    lang,
    selector: (
      <label className="block text-sm">
        Language / भाषा
        <select
          aria-label="Language / भाषा"
          className={field}
          value={lang}
          onChange={(e) => choose(e.target.value as "en" | "hi")}
        >
          <option value="en">English</option>
          <option value="hi">हिन्दी</option>
        </select>
      </label>
    ),
  };
}
/** Invalidates late responses and clears displayed private data on session/focus changes. */
export function useBoundary(reset: () => void) {
  const [ready, setReady] = useState(false),
    [busy, setBusy] = useState(false),
    [failed, setFailed] = useState(false),
    [changed, setChanged] = useState(false);
  const generation = useRef(0),
    locked = useRef(false);
  useEffect(() => {
    let active = true;
    let unsubscribe: (() => void) | undefined;
    const expire = () => {
      generation.current++;
      locked.current = false;
    };
    const clear = () => {
      expire();
      setBusy(false);
      setChanged(true);
      setFailed(false);
      reset();
    };
    const visible = () => {
      if (document.visibilityState === "visible") clear();
    };
    try {
      if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") throw Error();
      unsubscribe = observeSessionChanges(clear);
      window.addEventListener("focus", clear);
      document.addEventListener("visibilitychange", visible);
      queueMicrotask(() => {
        if (active) setReady(true);
      });
    } catch {
      queueMicrotask(() => {
        if (active) setReady(false);
      });
    }
    return () => {
      active = false;
      expire();
      unsubscribe?.();
      window.removeEventListener("focus", clear);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [reset]);
  async function run(work: (current: () => boolean) => Promise<void>) {
    if (!ready || locked.current) return;
    locked.current = true;
    setBusy(true);
    setFailed(false);
    setChanged(false);
    const g = ++generation.current;
    const current = () => g === generation.current;
    try {
      await work(current);
    } catch {
      if (current()) setFailed(true);
    } finally {
      if (current()) {
        locked.current = false;
        setBusy(false);
      }
    }
  }
  return { ready, busy, failed, changed, run };
}
