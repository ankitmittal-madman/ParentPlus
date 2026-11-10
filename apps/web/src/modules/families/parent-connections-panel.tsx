"use client";
import { useCallback, useState } from "react";
import {
  familySession,
  familyChildren,
  childAcademies,
} from "@/lib/families/actions";
import { type Child, type RosterRow } from "./contracts";
import { useCopy, useBoundary, button, field, card } from "./shared";
export default function ParentConnectionsPanel() {
  const { t, selector } = useCopy();
  const [actor, setActor] = useState(""),
    [children, setChildren] = useState<Child[] | null>(null),
    [child, setChild] = useState(""),
    [connections, setConnections] = useState<RosterRow[] | null>(null),
    [error, setError] = useState(false);
  const reset = useCallback(() => {
    setActor("");
    setChildren(null);
    setChild("");
    setConnections(null);
    setError(false);
  }, []);
  const b = useBoundary(reset);
  async function load() {
    await b.run(async (current) => {
      reset();
      const s = await familySession();
      if (!current()) return;
      if (!s.ok) {
        setError(true);
        return;
      }
      const c = await familyChildren(s.data);
      if (!current()) return;
      if (!c.ok) {
        setError(true);
        return;
      }
      setActor(s.data);
      setChildren(c.data);
    });
  }
  async function inspect() {
    await b.run(async (current) => {
      setError(false);
      setConnections(null);
      const r = await childAcademies(actor, child);
      if (!current()) return;
      if (r.ok) setConnections(r.data);
      else setError(true);
    });
  }
  return (
    <section className={card} aria-label={t.connections}>
      <h2 className="text-lg font-bold">{t.connections}</h2>
      <div className="mt-3">{selector}</div>
      <button className={button} disabled={!b.ready || b.busy} onClick={load}>
        {t.checkChildren}
      </button>
      {children && (
        <>
          <label className="mt-3 block">
            {t.yourChild}
            <select
              aria-label={t.yourChild}
              className={field}
              value={child}
              disabled={b.busy}
              onChange={(e) => {
                setChild(e.target.value);
                setConnections(null);
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
          <button
            className={button}
            disabled={!child || b.busy}
            onClick={inspect}
          >
            {t.loadConnections}
          </button>
        </>
      )}
      {connections?.length === 0 && <p className="mt-3">{t.noConnections}</p>}
      {connections && connections.length > 0 && (
        <ul className="mt-3">
          {connections.map((c) => (
            <li key={c.id}>
              {c.name} · {t[c.status]}
            </li>
          ))}
        </ul>
      )}
      {b.busy && <p role="status">{t.loading}</p>}
      {(error || b.failed || b.changed) && (
        <p role="alert">{b.changed ? t.sessionChanged : t.failed}</p>
      )}
    </section>
  );
}
