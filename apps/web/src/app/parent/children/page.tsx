import { Suspense } from "react";
import { connection } from "next/server";
import CreatedChildrenPanel from "./created-children-panel";

export async function ParentChildrenGate() {
  await connection();
  return process.env.PARENTPLUS_ENABLE_PARENT_CHILD_LIST === "true"
    ? <CreatedChildrenPanel />
    : <p className="mt-4">Profiles are not available in this environment.</p>;
}

export default function ParentChildrenPage() {
  return <main className="mx-auto min-h-screen max-w-md bg-[#F3F5F1] px-5 py-8 text-[#22303A]">
    <h1 className="text-3xl font-extrabold">Parent profiles</h1>
    <Suspense fallback={<p className="mt-4">Checking availability…</p>}><ParentChildrenGate /></Suspense>
  </main>;
}
