# Frontend backlog — backend features audit

Last updated: 2026-07-05 (post-merge: sidebar + profile + lawyer referral backend)

This document tracks backend capabilities vs frontend implementation. See `CLAUDE.md` for the API contract.

**Legend**

| Status | Meaning |
|--------|---------|
| ✅ Done | Frontend wired and rendering |
| 🔶 Partial | Some UI exists; gaps remain |
| ❌ Missing | Backend ready; no frontend |
| 🔧 Backend incomplete | Backend stub; frontend blocked |

---

## Summary

| Area | Backend | Frontend | Gap |
|------|---------|----------|-----|
| Core decode (`POST /api/decode`) | ✅ | 🔶 | Unwraps `complete` only; ignores lawyer eligibility flags |
| Result display (summary, facts, verification, claims, actions) | ✅ | ✅ | — |
| Cursor-style sidebar + client sessions | — | ✅ | localStorage via `useSessions` |
| User profile CRUD | ✅ | ✅ | `ProfilePanel` + `api/client.ts` |
| Institution prompt (`needs_institution`) | ✅ | ❌ | Popup + re-submit with `institution` |
| Lawyer referrals (`POST /api/lawyers/recommend`) | ✅ | ❌ | Location popup + referral cards |
| Jurisdiction mismatch flag | 🔧 | ❌ | Backend detects; no mismatch field yet |
| Jurisdiction auto-detect + optional hint | ✅ | 🔶 | Auto-detect default; GB added; mismatch UI missing |
| Server document history (`GET /api/documents`) | ✅ | ❌ | Sessions are client-only |
| Health / demo-mode indicator | ✅ | ❌ | Optional banner |
| Profile autofill in generated letters | 🔧 | ❌ | `profile_id` not on `DecodeRequest` |

---

## ✅ Already implemented

- **Sidebar + multi-session** — `Sidebar`, `useSessions` (localStorage), forest palette
- **Paste & decode** — `PasteBox` → `POST /api/decode` (happy path)
- **Jurisdiction selector** — Auto-detect (default), IE, GB
- **Mock mode** — `VITE_MOCK=1` serves `mocks/sampleResult.ts`
- **Result display** — `ResultView`, `VerificationPanel`, `ClaimCard`, `ActionCard`
- **Profile CRUD** — `ProfilePanel`, types in `types.ts`, API in `client.ts`
- **Disclaimer** — footer in `App.tsx`

---

## ❌ Backend ready — frontend needed

### 1. Institution identification popup (high priority)

**Backend:** `POST /api/decode` returns `DecodeResponse` with `status: "needs_institution"` and `institution_prompt` (message + suggestions).

**Current behaviour:** `decode()` throws a generic error. No UI to pick RTB / Citizens Information / etc.

**Tasks**

- [ ] Change `decode()` to return full `DecodeResponse` (or add `decodeDocument()` alongside)
- [ ] Modal/popup showing `institution_prompt.message` and suggestion buttons
- [ ] Re-submit with `institution: { body_id, display_name }` on selection
- [ ] Handle free-text institution when slug unknown

---

### 2. Lawyer referral flow (high priority)

**Backend:** Pipeline sets `lawyer_referral_eligible` + `lawyer_referral_reason` on complete decodes. Actual referrals via `POST /api/lawyers/recommend` with decode context + user location.

**Current behaviour:** Eligibility flags are discarded when `decode()` unwraps `result` only.

**Tasks**

- [ ] Surface `lawyer_referral_eligible` from decode response
- [ ] Popup: "We couldn't find strong sources — where are you located?" (city/county)
- [ ] Add `recommendLawyers()` to `api/client.ts`
- [ ] Display `LawyerReferral` cards (name, firm, practice area, phone, url)
- [ ] Optional: pre-fill location from saved profile

---

### 3. Jurisdiction mismatch warning (medium priority)

**Product intent:** User may set a jurisdiction hint. Backend classifies document jurisdiction independently. UI should flag when they differ.

**Backend gap:** No `jurisdiction_hint` vs `detected_jurisdiction` fields on `DecodeResult` yet — classify overwrites to detected value.

**Tasks**

- [ ] Backend: add `jurisdiction_mismatch: bool` and/or `user_jurisdiction_hint` to `DecodeResponse` or `DecodeResult`
- [ ] Frontend: warning banner when hint ≠ detected (e.g. user picked IE, document is GB)
- [ ] When auto-detect returns `UNK`, prompt user to select jurisdiction and re-decode

---

### 4. Server document history (medium priority)

**Backend:** `GET /api/documents`, `GET /api/documents/{id}` — SQLite persistence on every decode.

**Current behaviour:** Sidebar sessions are localStorage only; server history unused.

**Tasks**

- [ ] Add `listDocuments()` / `getDocument(id)` to `api/client.ts`
- [ ] Option A: replace localStorage sessions with server list
- [ ] Option B: sync completed decodes to server, keep drafts local
- [ ] Show `created_at` (requires schema extension or list endpoint)

---

### 5. Health / demo banner (low priority)

**Backend:** `GET /api/health` → `{ status, demo_mode, tls_enabled, profile_encryption }`

**Tasks**

- [ ] Add `getHealth()` to `api/client.ts`
- [ ] Subtle banner when `demo_mode` is true

---

## 🔶 Partially implemented

### Decode response handling

`client.ts` unwraps `status === "complete"` → `result`. Does not expose:

- `institution_prompt` (needs_institution)
- `lawyer_referral_eligible` / `lawyer_referral_reason`

### Profile autofill in letters

Helpers exist in `profile_autofill.py` but `profile_id` is not accepted on `DecodeRequest`. Profile is stored but not injected into generated actions.

---

## API quick reference

| Method | Path | Frontend status |
|--------|------|-----------------|
| `POST` | `/api/decode` | 🔶 happy path only |
| `GET` | `/api/documents` | ❌ |
| `GET` | `/api/documents/{id}` | ❌ |
| `POST` | `/api/lawyers/recommend` | ❌ |
| `GET` | `/api/health` | ❌ |
| `POST` | `/api/profile` | ✅ |
| `GET` | `/api/profile/{id}` | ✅ |
| `PUT` | `/api/profile/{id}` | ✅ |
| `DELETE` | `/api/profile/{id}` | ❌ (no delete UI) |

---

## Suggested implementation order

1. **Institution popup** — unblocks decodes for unknown authorities
2. **Lawyer referral popup + cards** — completes the "can't ground it" path
3. **Jurisdiction mismatch** — needs small backend schema addition first
4. **Server history sync** — optional; sessions work for demo
5. **Health banner** — quick win
6. **Profile autofill** — after backend accepts `profile_id` on decode

---

## Files to touch

| File | Purpose |
|------|---------|
| `src/types.ts` | Keep synced with `schemas.py` |
| `src/api/client.ts` | Full `DecodeResponse`, lawyers, health, history |
| `src/components/PasteBox.tsx` | Institution modal trigger |
| `src/components/ResultView.tsx` | Lawyer referrals, mismatch banner |
| New: `InstitutionPromptModal.tsx` | Institution picker |
| New: `LawyerReferralModal.tsx` | Location prompt + results |
