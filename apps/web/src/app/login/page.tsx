"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { requestEmailOtp } from "@/lib/auth/request-email-otp";
import { verifyEmailOtp } from "@/lib/auth/verify-email-otp";
import { signOut } from "@/lib/auth/sign-out";
import { getSessionStatus } from "@/lib/auth/session-status";
import { observeSessionChanges } from "@/lib/auth/session-observer";

const EMAIL_FORMAT = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [accountMode, setAccountMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState("");
  const [verified, setVerified] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState("");
  const sessionCheckEnabled = process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP === "true";
  const [sessionCheck, setSessionCheck] = useState<"checking" | "ready" | "unavailable" | "uncertain">(
    sessionCheckEnabled ? "checking" : "ready"
  );
  const [sessionAttempt, setSessionAttempt] = useState(0);
  const submittingRef = useRef(false);
  const successRef = useRef<HTMLParagraphElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const codeRef = useRef<HTMLInputElement>(null);
  const focusCodeAfterRequest = useRef(false);
  const focusEmailAfterSignOut = useRef(false);
  const authGeneration = useRef(0);
  const pendingAuthChange = useRef(false);
  const pendingResumeCheck = useRef(false);
  const verifiedRef = useRef(false);
  const observerFailed = useRef(false);
  const signOutUncertain = useRef(false);
  const mounted = useRef(true);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setVerifiedState = useCallback((value: boolean) => {
    verifiedRef.current = value;
    setVerified(value);
  }, []);

  const scheduleSessionRefresh = useCallback(() => {
    if (!mounted.current || signOutUncertain.current || submittingRef.current ||
        (!pendingAuthChange.current && !pendingResumeCheck.current)) return;
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => {
      refreshTimer.current = null;
      if (!mounted.current || signOutUncertain.current || submittingRef.current ||
          (!pendingAuthChange.current && !pendingResumeCheck.current)) return;
      const changed = pendingAuthChange.current;
      pendingAuthChange.current = false;
      pendingResumeCheck.current = false;
      if (changed) setVerifiedState(false);
      else authGeneration.current += 1;
      setSessionCheck("checking");
      setSignOutError("");
      setSessionAttempt((attempt) => attempt + 1);
    }, 0);
  }, [setVerifiedState]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      authGeneration.current += 1;
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
    };
  }, []);

  useEffect(() => {
    if (!sessionCheckEnabled) return;
    function recheckOnReturn() {
      if (!mounted.current || signOutUncertain.current || sessionCheck === "unavailable") return;
      if (!submittingRef.current) authGeneration.current += 1;
      pendingResumeCheck.current = true;
      if (verified) setEmail("");
      setSessionCheck("checking");
      scheduleSessionRefresh();
    }
    function onVisibilityChange() {
      if (document.visibilityState === "visible") recheckOnReturn();
    }
    window.addEventListener("focus", recheckOnReturn);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      window.removeEventListener("focus", recheckOnReturn);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [sessionCheckEnabled, verified, sessionCheck, scheduleSessionRefresh]);

  useEffect(() => {
    if (!sessionCheckEnabled) return;
    observerFailed.current = false;
    let active = true;
    let unsubscribe: (() => void) | undefined;
    try {
      unsubscribe = observeSessionChanges((event) => {
        if (!mounted.current) return;
        authGeneration.current += 1;
        if (event !== "TOKEN_REFRESHED") setEmail("");
        focusCodeAfterRequest.current = false;
        if (signOutUncertain.current) return;
        pendingAuthChange.current = true;
        setSubmitted(false);
        setCode("");
        setCodeError("");
        setError("");
        setSessionCheck("checking");
        scheduleSessionRefresh();
      });
    } catch {
      observerFailed.current = true;
      queueMicrotask(() => { if (active) setSessionCheck("unavailable"); });
    }
    return () => { active = false; unsubscribe?.(); };
  }, [sessionCheckEnabled, sessionAttempt, scheduleSessionRefresh]);

  useEffect(() => {
    if (submitted && sessionCheck === "ready" && !loading && focusCodeAfterRequest.current && codeRef.current) {
      focusCodeAfterRequest.current = false;
      focusEmailAfterSignOut.current = false;
      codeRef.current.focus();
    }
  }, [submitted, sessionCheck, loading]);

  useEffect(() => {
    if (verified) successRef.current?.focus();
    else if (focusEmailAfterSignOut.current) {
      emailRef.current?.focus();
      focusEmailAfterSignOut.current = false;
    }
  }, [verified, sessionCheck]);

  useEffect(() => {
    if (!sessionCheckEnabled || observerFailed.current) return;
    let cancelled = false;
    const generation = authGeneration.current;
    getSessionStatus().then((result) => {
      if (cancelled || generation !== authGeneration.current) return;
      if (result.state === "unavailable") {
        setSessionCheck("unavailable");
      } else {
        if (result.state === "signed-out" && sessionAttempt > 0) {
          if (verifiedRef.current) setEmail("");
          focusEmailAfterSignOut.current = true;
        }
        if (result.state === "signed-in") {
          setAccountMode("sign-in");
          setEmail("");
          setSubmitted(false);
          setCode("");
          setCodeError("");
          setError("");
        }
        setVerifiedState(result.state === "signed-in");
        setSessionCheck("ready");
      }
    }).catch(() => {
      if (!cancelled && generation === authGeneration.current) setSessionCheck("unavailable");
    });
    return () => { cancelled = true; };
  }, [sessionCheckEnabled, sessionAttempt, setVerifiedState]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (submittingRef.current) return;

    const normalized = email.trim().toLowerCase();
    const retrying = submitted;

    if (!EMAIL_FORMAT.test(normalized)) {
      setError("Enter a valid email address.");
      setSubmitted(false);
      return;
    }

    submittingRef.current = true;
    const generation = authGeneration.current;
    setLoading(true);
    setError("");
    setSubmitted(false);
    setVerifiedState(false);
    if (!retrying) setCode("");
    setCodeError("");

    try {
      const result = accountMode === "sign-up"
        ? await requestEmailOtp(normalized, "sign-up")
        : await requestEmailOtp(normalized);
      if (!mounted.current || generation !== authGeneration.current) return;

      if (!result.success) {
        setError(retrying ? "Unable to confirm the latest request. Please try again." : result.error ?? "Unable to send verification code.");
        if (retrying) { focusCodeAfterRequest.current = true; setSubmitted(true); }
        return;
      }

      setEmail(normalized);
      setCode("");
      focusCodeAfterRequest.current = true;
      setSubmitted(true);
    } catch {
      if (mounted.current && generation === authGeneration.current) {
        setError(retrying ? "Unable to confirm the latest request. Please try again." : "Unable to send verification code. Please try again.");
        if (retrying) { focusCodeAfterRequest.current = true; setSubmitted(true); }
      }
    } finally {
      submittingRef.current = false;
      if (mounted.current) { setLoading(false); scheduleSessionRefresh(); }
    }
  }

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current || !submitted) return;
    submittingRef.current = true;
    const generation = authGeneration.current;
    setVerifying(true);
    setCodeError("");
    try {
      const result = await verifyEmailOtp(email, code);
      if (!mounted.current || generation !== authGeneration.current) return;
      if (!result.success) {
        setCodeError(result.error ?? "Verification failed. Please try again.");
        return;
      }
      setVerifiedState(true);
      setAccountMode("sign-in");
      setSubmitted(false);
      setCode("");
    } catch {
      if (mounted.current && generation === authGeneration.current) setCodeError("Verification failed. Please try again.");
    } finally {
      submittingRef.current = false;
      if (mounted.current) { setVerifying(false); scheduleSessionRefresh(); }
    }
  }

  async function handleSignOut() {
    if (submittingRef.current || !verified) return;
    submittingRef.current = true;
    const generation = authGeneration.current;
    let uncertain = false;
    setSigningOut(true);
    setSignOutError("");
    try {
      const result = await signOut();
      if (!mounted.current) return;
      if (!result.success) {
        uncertain = true;
        signOutUncertain.current = true;
        pendingAuthChange.current = false;
        pendingResumeCheck.current = false;
        setVerifiedState(false);
        setSessionCheck("uncertain");
        setSignOutError(result.error ?? "Unable to confirm sign-out. Please try again.");
        return;
      }
      if (generation !== authGeneration.current) return;
      focusEmailAfterSignOut.current = true;
      setAccountMode("sign-in");
      setEmail("");
      setVerifiedState(false);
    } catch {
      if (mounted.current) {
        uncertain = true;
        signOutUncertain.current = true;
        pendingAuthChange.current = false;
        pendingResumeCheck.current = false;
        setVerifiedState(false);
        setSessionCheck("uncertain");
        setSignOutError("Unable to confirm sign-out. Please try again.");
      }
    } finally {
      submittingRef.current = false;
      if (mounted.current) { setSigningOut(false); if (!uncertain) scheduleSessionRefresh(); }
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-5 py-10">
      <section className="w-full max-w-md rounded-3xl bg-white p-7 shadow-sm">
        <div
          aria-hidden="true"
          className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand text-2xl text-white"
        >
          ✦
        </div>

        <h1 className="text-2xl font-bold text-ink">
          Welcome to Parent Plus
        </h1>

        <p className="mt-2 text-sm leading-6 text-muted">
          {accountMode === "sign-up" ? "Create an account with your email." : "Sign in with your email to continue."}
        </p>

        {sessionCheck === "checking" && <p role="status" className="mt-5 text-sm text-muted">Checking your session...</p>}
        {sessionCheck === "uncertain" && (
          <div className="mt-5 space-y-3">
            <p role="alert" className="text-sm text-red-700">{signOutError}</p>
            <button type="button" onClick={() => { signOutUncertain.current = false; setSignOutError(""); setSessionCheck("checking"); setSessionAttempt((attempt) => attempt + 1); }} className="w-full rounded-xl bg-brand px-5 py-3 font-semibold text-white">Check session</button>
          </div>
        )}
        {sessionCheck === "unavailable" && (
          <div className="mt-5 space-y-3">
            <p role="alert" className="text-sm text-red-700">Unable to check your session. Please try again.</p>
            <button type="button" onClick={() => { setSessionCheck("checking"); setSessionAttempt((attempt) => attempt + 1); }} className="w-full rounded-xl bg-brand px-5 py-3 font-semibold text-white">Try again</button>
          </div>
        )}

        {sessionCheck === "ready" && !verified && <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-semibold text-ink"
            >
              Email address
            </label>

            <input
              ref={emailRef}
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              disabled={loading || verifying}
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                focusCodeAfterRequest.current = false;
                setError("");
                setSubmitted(false);
                setVerifiedState(false);
                setCode("");
                setCodeError("");
              }}
              aria-invalid={Boolean(error) && !EMAIL_FORMAT.test(email.trim().toLowerCase())}
              aria-describedby={error ? "email-error" : undefined}
              placeholder="you@example.com"
              className="w-full rounded-xl border border-gray-300 px-4 py-3 text-base text-ink outline-none focus-visible:ring-2 focus-visible:ring-brand"
            />

            {error && (
              <p id="email-error" role="alert" className="mt-2 text-sm text-red-700">
                {error}
              </p>
            )}
          </div>

          {process.env.NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP === "true" && (
            <button
              type="button"
              disabled={loading || verifying}
              onClick={() => {
                if (submittingRef.current) return;
                setAccountMode((mode) => mode === "sign-in" ? "sign-up" : "sign-in");
                focusCodeAfterRequest.current = false;
                setSubmitted(false);
                setCode("");
                setCodeError("");
                setError("");
              }}
              className="text-sm font-semibold text-brand underline disabled:opacity-60"
            >
              {accountMode === "sign-in" ? "Create account" : "Sign in instead"}
            </button>
          )}
          <button
            type="submit"
            disabled={loading || verifying}
            className="w-full rounded-xl bg-brand px-5 py-3 font-semibold text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Sending..." : submitted ? "Request another code" : "Continue"}
          </button>
        </form>}

        {sessionCheck === "ready" && submitted && (
          <>
            <p role="status" className="mt-5 text-sm text-muted">
              {error ? "The latest request could not be confirmed. You can try a code or request another." : "Verification request accepted. Check your email for instructions."}
            </p>
            <form onSubmit={handleVerify} noValidate className="mt-5 space-y-3">
              <label htmlFor="verification-code" className="block text-sm font-semibold text-ink">
                Verification code
              </label>
              <p id="code-hint" className="text-sm text-muted">Enter the six-digit code from your email.</p>
              <input
                id="verification-code"
                ref={codeRef}
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(event) => { setCode(event.target.value); setCodeError(""); }}
                disabled={loading || verifying}
                aria-invalid={Boolean(codeError)}
                aria-describedby={codeError ? "code-hint code-error" : "code-hint"}
                className="w-full rounded-xl border border-gray-300 px-4 py-3 focus-visible:ring-2 focus-visible:ring-brand"
              />
              {codeError && <p id="code-error" role="alert" className="text-sm text-red-700">{codeError}</p>}
              <button type="submit" disabled={loading || verifying} className="w-full rounded-xl bg-brand px-5 py-3 font-semibold text-white disabled:opacity-60">
                {verifying ? "Verifying..." : "Verify code"}
              </button>
            </form>
          </>
        )}
        {sessionCheck === "ready" && verified && (
          <div className="mt-5 space-y-3">
            {!signOutError && !signingOut && <p ref={successRef} tabIndex={-1} role="status" className="text-sm text-muted">Signed in.</p>}
            {signOutError && <p role="alert" className="text-sm text-red-700">{signOutError}</p>}
            {!signingOut && process.env.NEXT_PUBLIC_ENABLE_PARENT_PROFILE_LINK === "true" && <Link href="/parent/children" prefetch={false} className="block text-sm font-semibold text-brand underline">View profiles you created</Link>}
            <button type="button" onClick={handleSignOut} disabled={signingOut} className="w-full rounded-xl bg-brand px-5 py-3 font-semibold text-white disabled:opacity-60">
              {signingOut ? "Signing out..." : "Sign out"}
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
