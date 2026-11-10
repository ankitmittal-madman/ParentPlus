"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  familySession,
  familyChildren,
  previewFamilyInvite,
  acceptFamilyInvite,
  childAcademies,
} from "@/lib/families/actions";
import { isToken, type Child, type Preview, type RosterRow } from "./contracts";
import { useCopy, useBoundary, button, field, card } from "./shared";
export default function JoinPanel() {
  const { t, selector } = useCopy();
  const [token, setToken] = useState(""),
    [actor, setActor] = useState(""),
    [children, setChildren] = useState<Child[]>([]),
    [child, setChild] = useState(""),
    [confirmed, setConfirmed] = useState(false),
    [preview, setPreview] = useState<Preview | null>(null),
    [saved, setSaved] = useState(false),
    [attempted, setAttempted] = useState(false),
    [notice, setNotice] = useState<keyof typeof t | null>(null),
    [connections, setConnections] = useState<RosterRow[] | null>(null);
  // The fragment never reaches the server URL. Remove it before any server action.
  useEffect(() => {
    const fragment = location.hash.slice(1);
    history.replaceState(
      history.state,
      "",
      location.pathname + location.search,
    );
    queueMicrotask(() => {
      if (isToken(fragment)) setToken(fragment);
    });
  }, []);
  const reset = useCallback(() => {
    setActor("");
    setChildren([]);
    setChild("");
    setConfirmed(false);
    setPreview(null);
    setSaved(false);
    setAttempted(false);
    setNotice(null);
    setConnections(null);
  }, []);
  const b = useBoundary(reset);
  async function check() {
    await b.run(async (current) => {
      reset();
      const s = await familySession();
      if (!current()) return;
      if (!s.ok) {
        setNotice("failed");
        return;
      }
      const p = await previewFamilyInvite(s.data, token);
      if (!current()) return;
      if (!p.ok) {
        setNotice("inviteFailed");
        return;
      }
      const c = await familyChildren(s.data);
      if (!current()) return;
      if (!c.ok) {
        setNotice("failed");
        return;
      }
      setActor(s.data);
      setPreview(p.data);
      setChildren(c.data);
    });
  }
  async function accept() {
    await b.run(async (current) => {
      if (!confirmed || !child) return;
      setAttempted(true);
      setNotice(null);
      const r = await acceptFamilyInvite(actor, token, child).catch(() => ({
        ok: false as const,
      }));
      if (!current()) return;
      if (!r.ok) {
        setNotice("acceptUnknown");
        return;
      }
      setSaved(true);
      setNotice(null);
      const links = await childAcademies(actor, child);
      if (current() && links.ok) setConnections(links.data);
    });
  }
  return (
    <section>
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-3xl font-extrabold">{t.joinTitle}</h1>
        <div className="w-32 shrink-0">{selector}</div>
      </div>
      <p className="mt-4 text-sm">{t.joinIntro}</p>
      <div className={card}>
        {!token && <p>{t.invalidLink}</p>}
        <Link
          href="/login"
          prefetch={false}
          className="block text-sm font-semibold text-[#1F6F6B] underline"
        >
          {t.signIn}
        </Link>
        {!b.ready && <p role="status">{t.monitorUnavailable}</p>}
        <button
          className={button}
          disabled={!token || !b.ready || b.busy}
          onClick={check}
        >
          {t.checkInvite}
        </button>
        {preview && (
          <>
            <h2 className="mt-5 text-xl font-bold">{preview.academyName}</h2>
            <p className="mt-2 text-sm">
              {t.expires}: {new Date(preview.expiresAt).toLocaleDateString()}
            </p>
            {preview.state === "accepted" && <p className="mt-2">{t.used}</p>}
            {children.length === 0 && <p className="mt-3">{t.noChildren}</p>}
            {children.length > 0 && (
              <>
                <label className="mt-4 block">
                  {t.yourChild}
                  <select
                    aria-label={t.yourChild}
                    className={field}
                    disabled={b.busy || saved || attempted}
                    value={child}
                    onChange={(e) => {
                      setChild(e.target.value);
                      setConfirmed(false);
                    }}
                  >
                    <option value="">{t.choose}</option>
                    {children.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="mt-4 flex items-start gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={confirmed}
                    disabled={b.busy || saved || attempted}
                    onChange={(e) => setConfirmed(e.target.checked)}
                  />
                  {t.declaration}
                </label>
                <p className="mt-3 text-xs text-[#5C6B73]">{t.privacy}</p>
                <button
                  className={button}
                  disabled={b.busy || !child || !confirmed || saved}
                  onClick={accept}
                >
                  {t.confirm}
                </button>
              </>
            )}
          </>
        )}
        <Link
          className="mt-4 block text-sm font-semibold text-[#1F6F6B] underline"
          href="/parent/children"
          prefetch={false}
        >
          {t.ownProfiles}
        </Link>
      </div>
      {saved && (
        <div className={card}>
          <p role="status">{t.connected}</p>
          {connections && (
            <ul className="mt-3">
              {connections.map((c) => (
                <li key={c.id}>
                  {c.name} · {t[c.status]}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {b.busy && (
        <p role="status" className="mt-4">
          {t.loading}
        </p>
      )}
      {(notice || b.failed || b.changed) && (
        <p role="alert" className="mt-4">
          {notice ? t[notice] : b.failed ? t.failed : t.sessionChanged}
        </p>
      )}
    </section>
  );
}
