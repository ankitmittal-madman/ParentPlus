import { Suspense } from "react";
import { connection } from "next/server";
import { founderConfig } from "@/lib/founder/runtime";
import FounderControls from "./controls-panel";
async function Gate() { await connection(); return founderConfig() ? <FounderControls /> : <p>Founder controls require the configured testing environment.</p>; }
export default function FounderPage() { return <main className="mx-auto min-h-screen max-w-2xl bg-paper p-6 text-ink"><h1 className="text-3xl font-bold">ParentPlus founder testing</h1><Suspense fallback={<p>Checking local sandbox…</p>}><Gate /></Suspense></main>; }
