"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { familySession } from "@/lib/families/actions";
import { observeSessionChanges } from "@/lib/auth/session-observer";
import { uuid, id } from "./validation";
/** Private read generations are disposable. Durable pending operations live outside this boundary. */
export function useSessionBoundary(clearPrivate: () => void) {
  const authority = useRef(0);
  const generation = useRef(0);
  const alive = useRef(false);
  const callbacks = useRef(clearPrivate);
  const [actorId, setActor] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    callbacks.current = clearPrivate;
  });
  const capture = useCallback(() => {
    const stamp = generation.current;
    return () => alive.current && stamp === generation.current;
  }, []);
  const invalidateView = useCallback(() => {
    generation.current++;
  }, []);
  useEffect(() => {
    alive.current = true;
    let unsubscribe: (() => void) | undefined;
    const clear = () => {
      authority.current++;
      generation.current++;
      setActor(null);
      callbacks.current();
    };
    const verify = async () => {
      clear();
      if (document.visibilityState !== "visible")
        return;
      const stamp = authority.current;
      try {
        const session = await familySession();
        if (!alive.current || stamp !== authority.current)
          return;
        setActor(session.ok && uuid(session.data) ? id(session.data) : null);
      }
      catch {
        /* View remains cleared. */
      }
    };
    const visible = () => {
      if (document.visibilityState === "visible")
        void verify();
      else
        clear();
    };
    try {
      if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true")
        throw Error("disabled");
      unsubscribe = observeSessionChanges(() => {
        void verify();
      });
      window.addEventListener("focus", verify);
      document.addEventListener("visibilitychange", visible);
      queueMicrotask(() => {
        if (alive.current) {
          setReady(true);
          void verify();
        }
      });
    }
    catch {
      queueMicrotask(() => {
        if (alive.current)
          clear();
      });
    }
    return () => {
      alive.current = false;
      invalidateView();
      unsubscribe?.();
      window.removeEventListener("focus", verify);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [invalidateView]);
  return { actorId, ready, capture, invalidateView };
}
