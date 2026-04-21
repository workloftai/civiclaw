# civiclaw admin UI

Minimal Next.js admin for reviewing audit logs and signing off on `human_in_the_loop` actions — the enforcement layer for EU AI Act Article 14.

## What it does

- **Feed** — live view of the audit log (`/api/audit`)
- **Pending approvals** — actions that completed but are blocked on a human sign-off
- **Approve / reject** — write an `oversight.approved` or `oversight.rejected` entry to the audit log
- **Chain verification** — one-click verify the audit log is untampered

## Stack

Next.js 16 App Router + Tailwind. Reads `.audit/civiclaw.jsonl` via the Node filesystem API. No external dependencies for the core loop — deliberately minimal so it can run inside a council's locked-down environment.

## Run

```bash
cd ui
npm install
npm run dev
# open http://localhost:3000
```

## Not yet

This is a v0.1 scaffold. Real admin UI adds:

- Per-skill filtering
- Export to CSV / PDF for ICO / regulator submissions
- Role-based sign-off (IGO / DPO / deputy)
- Rich diff view on redactions
- Search over audit events

Tracked in issues.
