import { Suspense } from "react";
import { connection } from "next/server";
import WorkspaceForm from "./workspace-form";
async function Gate() {
  await connection();
  return process.env.PARENTPLUS_ENABLE_WORKSPACE_CREATION === "true"
    ? <WorkspaceForm /> : <p>Workspace setup is not available in this environment.</p>;
}
export default function CoachOnboardingPage() {
  return <main className="mx-auto min-h-screen max-w-md bg-paper p-6 text-ink"><h1 className="text-3xl font-bold">Set up your workspace</h1><Suspense fallback={<p>Checking availability…</p>}><Gate /></Suspense></main>;
}
