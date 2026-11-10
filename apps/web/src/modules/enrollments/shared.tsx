"use client";
import { useEffect, useRef, useState } from "react";
import { observeSessionChanges } from "@/lib/auth/session-observer";
import { familySession } from "@/lib/families/actions";
import en from "../../../messages/en.json";
import hi from "../../../messages/hi.json";
import { field } from "@/modules/families/shared";
export { button, field, card } from "@/modules/families/shared";

export function useEnrollmentCopy() {
  const [lang, setLang] = useState<"en" | "hi">("en");
  useEffect(() => {
    let alive = true;
    queueMicrotask(() => {
      try {
        const value = localStorage.getItem("parentplus:enrollment-language");
        if (alive && (value === "en" || value === "hi")) setLang(value);
      } catch {
        /* Optional preference. */
      }
    });
    return () => {
      alive = false;
    };
  }, []);
  const selector = (
    <label className="block text-xs text-[#5C6B73]">
      Enrolment language / नामांकन की भाषा
      <select
        className={field}
        aria-label="Enrolment language / नामांकन की भाषा"
        value={lang}
        onChange={(event) => {
          const value = event.target.value as "en" | "hi";
          setLang(value);
          try {
            localStorage.setItem("parentplus:enrollment-language", value);
          } catch {
            /* Optional preference. */
          }
        }}
      >
        <option value="en">English</option>
        <option value="hi">हिन्दी</option>
      </select>
    </label>
  );
  return { t: lang === "hi" ? hi.enrollments : en.enrollments, selector };
}

type Work = (actor: string, current: () => boolean) => Promise<void>;
/** Each read/write starts with a verified server session; invalidation clears private views immediately. */
export function useEnrollmentBoundary(reset: () => void, autoLoad: Work) {
  const generation = useRef(0),
    locked = useRef(false),
    enabled = useRef(false);
  const callbacks = useRef({ reset, autoLoad });
  const [ready, setReady] = useState(false),
    [busy, setBusy] = useState(false),
    [failed, setFailed] = useState(false);
  useEffect(() => {
    callbacks.current = { reset, autoLoad };
  });
  const run = async (work: Work) => {
    if (!enabled.current || locked.current) return;
    locked.current = true;
    setBusy(true);
    setFailed(false);
    const stamp = ++generation.current;
    const current = () => generation.current === stamp && enabled.current;
    try {
      const session = await familySession();
      if (!current()) return;
      if (!session.ok) {
        callbacks.current.reset();
        setFailed(true);
        return;
      }
      await work(session.data, current);
    } catch {
      if (current()) {
        callbacks.current.reset();
        setFailed(true);
      }
    } finally {
      if (current()) {
        locked.current = false;
        setBusy(false);
      }
    }
  };
  const runRef = useRef(run);
  useEffect(() => {
    runRef.current = run;
  });
  useEffect(() => {
    let alive = true,
      unsubscribe: (() => void) | undefined;
    const expire = () => {
      generation.current++;
      locked.current = false;
    };
    const clearAndLoad = () => {
      expire();
      callbacks.current.reset();
      setBusy(false);
      setFailed(false);
      queueMicrotask(() => {
        if (alive) void runRef.current(callbacks.current.autoLoad);
      });
    };
    const visible = () => {
      if (document.visibilityState === "visible") clearAndLoad();
    };
    try {
      if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true")
        throw Error("monitor disabled");
      unsubscribe = observeSessionChanges(clearAndLoad);
      enabled.current = true;
      window.addEventListener("focus", clearAndLoad);
      document.addEventListener("visibilitychange", visible);
      queueMicrotask(() => {
        if (alive) {
          setReady(true);
          void runRef.current(callbacks.current.autoLoad);
        }
      });
    } catch {
      enabled.current = false;
    }
    return () => {
      alive = false;
      enabled.current = false;
      expire();
      unsubscribe?.();
      window.removeEventListener("focus", clearAndLoad);
      document.removeEventListener("visibilitychange", visible);
    };
  }, []);
  return { ready, busy, failed, run };
}
