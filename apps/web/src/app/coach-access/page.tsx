"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { signOut } from "@/lib/auth/sign-out";

export default function CoachAccessPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSignOut() {
    setBusy(true);
    setError("");
    const result = await signOut();
    if (result.success) {
      router.replace("/login");
      return;
    }
    setBusy(false);
    setError(result.error ?? "Unable to sign out. Please try again.");
  }

  return (
    <main className="mx-auto min-h-screen max-w-md bg-[#F3F5F1] px-5 py-8 text-[#22303A]">
      <section className="rounded-3xl bg-white p-6 shadow-sm">
        <p className="text-sm font-bold uppercase tracking-wide text-[#537C78]">Parent Plus</p>
        <h1 className="mt-3 text-3xl font-extrabold">Coach access required</h1>
        <p className="mt-3 leading-6 text-[#53616A]">Your account does not have an active coach membership in a workspace. Ask the workspace owner to invite you, then sign in again.</p>
        {process.env.NEXT_PUBLIC_ENABLE_WORKSPACE_ONBOARDING === "true" && <Link href="/coach-onboarding" prefetch={false} className="mt-5 block font-semibold text-brand underline">Set up your own workspace</Link>}
        <button className="mt-6 min-h-12 w-full rounded-xl bg-[#22303A] px-4 font-bold text-white disabled:opacity-60" type="button" onClick={handleSignOut} disabled={busy}>
          {busy ? "Signing out…" : "Sign out"}
        </button>
        {error && <p className="mt-3 text-sm text-red-700" role="alert">{error}</p>}
      </section>
    </main>
  );
}
