"use client";
import { useState } from "react";
import Link from "next/link";
import { readFounderRecords, setFounderMembership } from "@/lib/founder/controls";
type Snapshot = Extract<Awaited<ReturnType<typeof readFounderRecords>>, { ok: true }>;
export default function FounderControls() {
  const [records, setRecords] = useState<Snapshot | null>(null);
  const [user, setUser] = useState(""); const [workspace, setWorkspace] = useState("");
  const [role, setRole] = useState("coach"); const [status, setStatus] = useState("active");
  const [notice, setNotice] = useState(""); const [busy, setBusy] = useState(false);
  async function refresh() { setBusy(true); try { const r = await readFounderRecords(); if (r.ok) { setRecords(r); setNotice(""); } else setNotice(r.error); } catch { setNotice("Unable to load test records."); } finally { setBusy(false); } }
  async function update() { setBusy(true); try { const r = await setFounderMembership({ userId: user, workspaceId: workspace, role, status }); setNotice(r.ok ? "Test membership updated. Reopen the coach area to test access." : r.error ?? "Update unavailable."); } catch { setNotice("Update unavailable."); } finally { setBusy(false); } }
  return <div className="mt-6 space-y-6">
    <p className="rounded-xl bg-amber-50 p-4">Founder testing sandbox. Sign in with a fictional .test email and code <strong>123456</strong>. Records are saved in the configured test database.</p>
    <nav className="flex flex-wrap gap-4 font-semibold text-brand underline"><Link href="/login">Switch test account</Link><Link href="/parent/children">Parent profiles</Link><Link href="/coach-onboarding">Create workspace</Link><Link href="/schedule">Coach classes</Link></nav>
    <section className="rounded-2xl bg-white p-5"><h2 className="text-xl font-bold">Saved test records</h2><button disabled={busy} onClick={refresh} className="mt-4 rounded-xl bg-brand p-3 text-white">Refresh test records</button>
      {records && <dl className="mt-4 grid grid-cols-2 gap-3">{Object.entries(records.counts).map(([table, count]) => <div key={table}><dt>{table.replaceAll("_", " ")}</dt><dd className="text-xl font-bold">{count}</dd></div>)}</dl>}
    </section>
    {records && <section className="space-y-3 rounded-2xl bg-white p-5"><h2 className="text-xl font-bold">Founder access override</h2><p>Assign or restore test access, or suspend it to exercise the normal coach access checks.</p>
      <label htmlFor="founder-user" className="block">Test account</label><select id="founder-user" className="w-full rounded-xl border p-3" value={user} onChange={e => setUser(e.target.value)}><option value="">Choose account</option>{records.users.map(u => <option key={u.id} value={u.id}>{u.email}</option>)}</select>
      <label htmlFor="founder-workspace" className="block">Test workspace</label><select id="founder-workspace" className="w-full rounded-xl border p-3" value={workspace} onChange={e => setWorkspace(e.target.value)}><option value="">Choose workspace</option>{records.workspaces.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}</select>
      <label htmlFor="founder-role" className="block">Role</label><select id="founder-role" className="w-full rounded-xl border p-3" value={role} onChange={e => setRole(e.target.value)}>{["owner", "admin", "coach"].map(r => <option key={r}>{r}</option>)}</select>
      <label htmlFor="founder-status" className="block">Access status</label><select id="founder-status" className="w-full rounded-xl border p-3" value={status} onChange={e => setStatus(e.target.value)}>{["active", "suspended", "removed"].map(r => <option key={r}>{r}</option>)}</select>
      <button disabled={busy || !user || !workspace} onClick={update} className="rounded-xl bg-brand p-3 text-white">Apply test access</button>
    </section>}
    {notice && <p role="status">{notice}</p>}
    <p className="text-sm text-muted">Available: parent profiles, workspace creation and weekly class setup. Enrollment, attendance, diary and fees are still being developed.</p>
  </div>;
}
