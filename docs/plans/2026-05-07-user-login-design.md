# User Login & Multi-Tenancy — Design

**Date**: 2026-05-07
**Status**: Approved, pending Q7 (auth provider) and implementation plan

## Goal

Add user accounts and multi-tenant isolation to ICDGuard so that multiple South African medical practices can use the app without seeing each other's data. Each practice has its own users, files, corrections, and billing. Reference data (ICD codes, tariff codes, PMB conditions, synonyms, hierarchies) stays globally shared.

## Decisions made (the ten Qs)

| # | Decision | Choice |
|---|---|---|
| 1 | Tenancy model | Multi-user per practice; each practice is an isolated tenant |
| 2 | Signup model | Hybrid: self-signup with 30-day free trial; paid plans via PayFast self-serve |
| 3 | Roles | Two: `admin` and `member` |
| 4 | Cross-practice learned data | Opt-in pooled learning; default per-practice only |
| 5 | Within-practice visibility | Shared with per-action audit log |
| 6 | Trial mechanics | 30 days, full features, then read-only until paid |
| 7 | Auth provider | **OPEN** — pending research; design absorbs either Clerk or self-built |
| 8 | Counting unit | Distinct `(patient + service date)` tuples; re-uploads count; dedupe accidental dupes |
| 9 | Existing data | Wipe on migration day (test data only) |
| 10 | Data residency | Defer SA hosting; stay on Vercel Postgres for v1 |
| 11 | Login security | Email+password, 30-day session, optional practice-wide MFA |

Pricing: banded volume tiers (no per-seat). Indicative bands: Starter (≤500 claims), Practice (≤2,000), Group (≤10,000). Numbers placeholder; refine after first 5 paying customers.

## Mental model

Three data layers:

1. **Reference data (shared, read-only)** — `icd_codes`, `tariff_codes`, `pmb_conditions`, `icd_synonyms`, `icd_chapters`, `icd_blocks`. Unchanged. The "library."
2. **Practice data (private, scoped)** — `sessions`, `claims`, `validation_issues`, `tariff_substitution_rules` (when not global), `action_log`. All filtered by `practice_id`. The "filing cabinet."
3. **Identity (per user)** — email, password, MFA. Lives in the auth provider's store. The "ID card."

## Schema changes

### New table: `practices`

```
id                    BIGINT GENERATED ALWAYS AS IDENTITY PK
external_id           UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE
name                  TEXT NOT NULL
billing_email         TEXT NOT NULL
plan                  TEXT NOT NULL    -- 'trial', 'starter', 'practice', 'group', 'expired'
trial_ends_at         TIMESTAMPTZ
billing_period_start  DATE NOT NULL    -- 1st of current month
claims_used           INT NOT NULL DEFAULT 0
claims_limit          INT NOT NULL    -- plan-derived
mfa_required          BOOLEAN NOT NULL DEFAULT FALSE
pooled_learning       BOOLEAN NOT NULL DEFAULT FALSE
payfast_token         TEXT
subscription_status   TEXT             -- 'trialing', 'active', 'past_due', 'cancelled'
subscription_started  TIMESTAMPTZ
next_billing_date     DATE
cancelled_at          TIMESTAMPTZ
created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
```

### New table: `practice_members`

```
id              BIGINT GENERATED ALWAYS AS IDENTITY PK
practice_id     BIGINT NOT NULL REFERENCES practices(id) ON DELETE CASCADE
auth_user_id    TEXT NOT NULL    -- Clerk user_id, or internal users PK as text
email           TEXT NOT NULL    -- denormalised for display
role            TEXT NOT NULL    -- 'admin', 'member'
invite_token    TEXT             -- one-time, NULL once accepted
invited_by      BIGINT REFERENCES practice_members(id)
invited_at      TIMESTAMPTZ
accepted_at     TIMESTAMPTZ
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE (practice_id, auth_user_id)
```

### New table: `action_log`

```
id           BIGINT GENERATED ALWAYS AS IDENTITY PK
practice_id  BIGINT NOT NULL REFERENCES practices(id) ON DELETE CASCADE
user_id      BIGINT NOT NULL REFERENCES practice_members(id)
action       TEXT NOT NULL    -- 'upload', 'correct_icd', 'correct_tariff', 'accept_warning', 'export', 'invite_member', 'remove_member', 'change_plan', ...
target_type  TEXT             -- 'session', 'claim', 'member'
target_id    BIGINT
details      JSONB            -- old/new values
created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
```

Indexes: `(practice_id, created_at DESC)`, `(practice_id, target_type, target_id)`.

### New table: `billing_events`

```
id              BIGINT GENERATED ALWAYS AS IDENTITY PK
practice_id     BIGINT NOT NULL REFERENCES practices(id)
event_type      TEXT NOT NULL    -- 'payment_succeeded', 'payment_failed', 'subscription_started', 'subscription_cancelled', 'plan_changed'
amount          NUMERIC(10,2)
payfast_payload JSONB
m_payment_id    TEXT             -- PayFast idempotency key
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE (m_payment_id)
```

### Changes to existing tables

- `sessions`: add `practice_id BIGINT NOT NULL REFERENCES practices(id) ON DELETE CASCADE`. Index `(practice_id, created_at DESC)`.
- `tariff_substitution_rules`: add `practice_id BIGINT NULL REFERENCES practices(id) ON DELETE CASCADE`. NULL = global pool. Index `(practice_id, original)`.
- `claims`, `validation_issues`: no change. Tenant scoping flows down via FK from `sessions`.

### Migration

`scripts/migrations/004-multitenancy.sql`. Single transaction. Steps:
1. Truncate `sessions`, `claims`, `validation_issues` (test data only — confirmed).
2. Truncate `tariff_substitution_rules` (rebuilds from re-uploaded corrections).
3. `CREATE TABLE` for the four new tables.
4. `ALTER TABLE` for the column additions.
5. `CREATE INDEX` for the new indexes.

## Flows

### Flow A — First-time admin signup

1. Visitor → `/signup`. Form: email, password, practice name (3 fields).
2. Verification email via ZeptoMail with one-time token.
3. Click link → atomically (single transaction) creates `practices` row (`plan='trial'`, `trial_ends_at=now+30d`, `claims_limit=1000`, `pooled_learning=FALSE`, `mfa_required=FALSE`) and `practice_members` row (`role='admin'`, `accepted_at=now`).
4. Logged in. Redirect to `/upload`. Banner: "30-day free trial — 1,000 claims. Invite colleagues from Settings."

### Flow B — Admin invites a member

1. Settings → Members → "Invite". Email entered.
2. Insert `practice_members` row, `accepted_at=NULL`, with one-time `invite_token`. ZeptoMail invite.
3. Recipient clicks link → if no auth identity, sets password (verifies email in same step). If existing identity in another practice → error (one practice per user in v1).
4. `accepted_at` set. Member can log in.

Pending invites visible in Members list with "Pending" badge and "Revoke invite" button. No auto-expiry in v1.

### Flow C — Route protection (the most important one)

Two layers:

1. **Next.js middleware**. Protected routes require auth session. If unauthenticated → `/login`. If authenticated but no `practice_member` row → support contact page. Anonymous routes: `/`, `/login`, `/signup`, `/invite`, `/verify`, `/forgot-password`, `/api/payfast/itn`.

2. **Tenant context wrapper.** Every API route and server component reads upload data via:
   ```ts
   withPractice(async (ctx) => {
     return db.sessions.findAll({ practice_id: ctx.practice_id, ... })
   })
   ```
   No raw query against `sessions`/`claims`/`validation_issues`/`tariff_substitution_rules`/`action_log` outside the wrapper. Enforced by code review and isolation tests.

### Flow D — Trial expiry & volume cap

Both checked at write time:

- **Upload**: count distinct `(patient_id, service_date)` from parsed CSV. Then atomically:
  ```sql
  UPDATE practices
  SET claims_used = claims_used + $n
  WHERE id = $p
    AND plan != 'expired'
    AND (trial_ends_at IS NULL OR trial_ends_at > now())
    AND claims_used + $n <= claims_limit * 1.20
  RETURNING claims_used
  ```
  0 rows → reject with reason (expired or over cap).

- **Reads / corrections / exports**: never gated. Practices retain access to existing data forever.

- **Banner thresholds**: 80% (yellow, email Admin), 95% (orange, email Admin), 100% (red, soft prompt), 120% (hard block on uploads only).

- **Monthly reset**: Vercel Cron daily at 02:00 UTC. For each practice with `billing_period_start < first-of-this-month`: set `claims_used = 0`, bump `billing_period_start`.

### Flow E — Plan upgrade (PayFast self-serve)

1. Settings → Billing → choose plan → click upgrade.
2. Redirect to PayFast hosted checkout. Practice details + plan price + recurring token request.
3. PayFast handles payment, returns to `/billing/success`.
4. ITN webhook → `/api/payfast/itn` → verify signature → idempotent by `m_payment_id` → update `practices` row (`plan`, `claims_limit`, `subscription_status='active'`, `payfast_token`, `next_billing_date`) → insert `billing_events` row → log to `action_log`.

### Flow F — Recurring payment

PayFast charges the token monthly. ITN → `billing_events` row, bump `next_billing_date`. If failure: `subscription_status='past_due'`, email Admin. 7-day grace + 2 retries. If still failing: `plan='expired'`, read-only mode.

### Flow G — Plan switch

Cancel current PayFast token, create new at new tier. **Defer policy**: change takes effect at next billing date, not mid-cycle (no proration in v1).

### Flow H — Cancellation

Settings → Billing → Cancel. API call to PayFast. Stays active until end of paid period, then `plan='expired'`.

## Security & error handling

| Failure mode | Mitigation |
|---|---|
| Tenant data leak | All queries via `withPractice()`; isolation test on every PR; optional Postgres RLS later |
| PayFast ITN missed | Idempotent handler keyed on `m_payment_id`; daily reconciliation cron; "Refresh" button |
| Race on `claims_used` | Atomic conditional UPDATE; upload + counter increment in one transaction |
| ZeptoMail outage | "Resend verification" button; pending state preserved in DB |
| Migration partial failure | Each migration in `BEGIN; ... COMMIT;` |
| Concurrent admin removal | Cannot remove last admin; promote a member first |

**MFA**: per-practice toggle. When `mfa_required=TRUE`, all members prompted to enrol TOTP on next login. Implementation depends on Q7 (Clerk: free; self-built: real work).

**Session length**: 30 days persistent. No idle timeout in v1.

**Password rules**: 8+ chars, mixed case + number. Standard.

**Email transport**:
- Zoho Mail for `support@icdguard.co.za` (human inbox).
- ZeptoMail for `noreply@icdguard.co.za` (verification, password reset, invites, threshold alerts).
- DNS (SPF/DKIM/DMARC) configured via Afrihost. Test with mail-tester.com after setup.

## Testing

- **Tenant isolation test (non-negotiable)**: two practices created, all read endpoints assert zero cross-leak. Runs on every PR.
- **Auth flows**: signup → verify → login → invite → accept → login as member.
- **Role enforcement**: member-attempts-admin-actions → 403.
- **Trial expiry**: time-travel `trial_ends_at` to past → upload rejected, exports allowed.
- **Volume cap**: parameterised at 80/95/100/119/121% — assert correct UI/block state.
- **Billing webhook**: mock PayFast ITN payloads (success, failure, cancellation) → state transitions correct.
- **Idempotency**: same ITN twice → one `billing_events` row.

## What we are NOT doing in v1 (YAGNI)

- Audit log browsing UI (data captured; SQL access for now).
- ICDGuard super-admin panel (manual SQL).
- Multi-practice users (one practice per user).
- Self-serve account deletion / data export (email-driven process).
- Idle session timeout.
- Per-user MFA (only practice-wide).
- Viewer-only role.
- SAML / SSO / Google login.
- Webhooks, API keys, programmatic access.
- Custom subdomains per practice.
- Annual plans.
- Branded invoice PDFs (use PayFast receipts).
- Mid-cycle plan proration.
- SA-hosted database.

## Open decisions

- **Q7: auth provider** — Clerk vs Auth.js vs self-built. Schema absorbs any choice via `auth_user_id TEXT`. Decide before implementation.
- **Pricing numbers** — refine after first 5 paying customers.
- **Signup form** — locked at 3 fields (email, password, practice name) unless reopened.

## Implementation phasing

| Phase | Scope | Dependencies |
|---|---|---|
| 1 | Migration 004, `withPractice()` wrapper, isolation test | None |
| 2 | Auth integration (login, signup, password reset, email verify) | Q7 decision |
| 3 | Practice management UI (Members, Settings, MFA toggle, pooled-learning toggle) | Phase 2 |
| 4 | Trial + volume gating (counter, banners, threshold emails, read-only mode) | Phase 1 |
| 5 | PayFast self-serve billing (plan UI, ITN webhook, billing_events, reconciliation cron) | Phase 4 |

Phases 1–4 deliver a working multi-tenant app with manual billing. Phase 5 closes the loop with self-serve PayFast subscriptions. Estimated 2–3 weeks of focused solo-developer work end to end.

## Next step

Once Q7 (auth provider) is decided, invoke the writing-plans skill to produce the detailed implementation plan.
