import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

type Entry = {
  ts: string;
  actor: string;
  skill: string;
  event: string;
  ref: string | null;
  data: Record<string, unknown>;
  prev_hash: string;
  hash: string;
};

const AUDIT_PATH = path.resolve(process.cwd(), "..", ".audit", "civiclaw.jsonl");

async function readAudit(): Promise<Entry[]> {
  try {
    const raw = await fs.readFile(AUDIT_PATH, "utf8");
    return raw
      .split("\n")
      .filter((l) => l.trim())
      .map((l) => JSON.parse(l) as Entry);
  } catch {
    return [];
  }
}

function verifyChain(entries: Entry[]): { ok: boolean; failAt: number | null } {
  const GENESIS = "0".repeat(64);
  let prev = GENESIS;
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (e.prev_hash !== prev) return { ok: false, failAt: i + 1 };
    const payloadForHash: Record<string, unknown> = { ...e };
    delete (payloadForHash as Partial<Entry>).hash;
    const canonical = JSON.stringify(
      Object.keys(payloadForHash)
        .sort()
        .reduce<Record<string, unknown>>((acc, k) => {
          acc[k] = (payloadForHash as Record<string, unknown>)[k];
          return acc;
        }, {}),
    );
    const expected = crypto.createHash("sha256").update(prev + canonical).digest("hex");
    if (e.hash !== expected) return { ok: false, failAt: i + 1 };
    prev = e.hash;
  }
  return { ok: true, failAt: null };
}

function findPendingApprovals(entries: Entry[]): Entry[] {
  // An entry that declared human_in_the_loop (data.requires_human_signoff === true)
  // and for which no subsequent oversight.approved event exists with matching ref.
  const approvedRefs = new Set(
    entries
      .filter((e) => e.event === "oversight.approved" && e.ref)
      .map((e) => e.ref as string),
  );
  return entries.filter(
    (e) => e.data && e.data["requires_human_signoff"] === true && e.ref && !approvedRefs.has(e.ref),
  );
}

export default async function Home() {
  const entries = await readAudit();
  const { ok, failAt } = verifyChain(entries);
  const pending = findPendingApprovals(entries);
  const latest = [...entries].reverse().slice(0, 20);

  return (
    <div className="container">
      <header style={{ marginBottom: 24 }}>
        <h1>civiclaw admin</h1>
        <p className="subtle">
          Audit log + human oversight layer.{" "}
          <span className={`verify ${ok ? "ok" : "err"}`}>
            {ok ? `chain verified — ${entries.length} entries` : `chain broken at entry ${failAt}`}
          </span>
        </p>
      </header>

      <section>
        <h2>Pending human sign-offs</h2>
        <div className="panel">
          {pending.length === 0 ? (
            <p className="subtle" style={{ margin: 0 }}>
              Nothing waiting on a human.{" "}
              <span className="tag ok">EU AI Act Art. 14: clear</span>
            </p>
          ) : (
            pending.map((e) => (
              <div key={e.hash} className="row">
                <div>
                  <div className="evt">
                    <span className={`tag ${e.skill}`}>{e.skill}</span>{" "}
                    <strong>{e.event}</strong>
                  </div>
                  <div className="ts">{new Date(e.ts).toLocaleString()}</div>
                </div>
                <div>
                  <span className="ref">{e.ref}</span>
                </div>
                <div>
                  <button>Approve</button>
                  <button className="secondary" style={{ marginLeft: 8 }}>
                    Reject
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <section>
        <h2>Recent audit events</h2>
        <div className="panel">
          {latest.length === 0 ? (
            <p className="subtle" style={{ margin: 0 }}>
              Audit log is empty. Run a skill to populate it.
            </p>
          ) : (
            latest.map((e) => (
              <div key={e.hash} className="row">
                <div style={{ flex: 1 }}>
                  <div className="evt">
                    <span className={`tag ${e.skill}`}>{e.skill}</span>{" "}
                    <strong>{e.event}</strong>
                  </div>
                </div>
                <div className="ref">{e.ref ?? "—"}</div>
                <div className="ts">{new Date(e.ts).toLocaleString()}</div>
              </div>
            ))
          )}
        </div>
      </section>

      <footer style={{ marginTop: 40, fontSize: 12, color: "var(--muted)" }}>
        <p>
          EU AI Act Article 12 compliant — append-only, SHA-256-hash-chained. EU AI Act Article 14
          compliant — {pending.length} pending human sign-off{pending.length === 1 ? "" : "s"}.
        </p>
        <p>civiclaw.{" "}<a href="https://workloft.ai" style={{ color: "var(--accent-2)" }}>workloft.ai</a></p>
      </footer>
    </div>
  );
}
