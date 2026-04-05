# CCSP Quiz App

Mobile-first quiz app for CCSP exam preparation with cloud sync and multi-user support.

## URLs
- **App**: https://ccsp-quiz.vercel.app
- **Admin Panel**: http://18.139.210.59:5001/admin.html
- **VPS Backend API**: http://18.139.210.59:5001

## Stack
- Next.js 14 (App Router), TypeScript, pure CSS
- Flask API on AWS Lightsail VPS (Python)
- SQLite database on VPS
- Vercel API routes as proxy (bypasses CORS)

## Quick Start
```bash
cd C:/Users/user/portfolio/ccsp-quiz
npm run dev
```

## Deploy
```bash
cd C:/Users/user/portfolio/ccsp-quiz
git remote remove origin
npx vercel --prod --yes
git remote add origin https://github.com/tommytang2414/ccsp-quiz.git
git push origin master
```

## Architecture

### Frontend (Vercel)
- `app/page.tsx` — main UI (login, home, quiz, done screens)
- `app/globals.css` — pure CSS utilities
- `lib/cloud-sync.ts` — API calls via Vercel proxy (`/api/*`)
- `lib/quiz-store.ts` — React state management
- `lib/questions.ts` — 1438 MCQ questions (full explanations + fixed options)

### API Proxy (Vercel)
- `app/api/register/route.ts` — POST, proxies to VPS `/api/register`
- `app/api/data/route.ts` — GET/PUT, proxies to VPS `/api/data`

### Backend (VPS Flask)
- `vps_api/app.py` — Flask API, DB at `/home/ubuntu/ccsp-quiz/auth.db`
- Admin token stored in DB `users` table

### Database Schema
```sql
codes(id, exam, code, used_by, used_at, created_at)
users(id, exam, token, data, created_at, updated_at)
```

## Authentication Flow
1. User enters activation code + their name on frontend
2. Vercel API route proxies to VPS `/api/register`
3. VPS validates (code exists AND code.name matches submitted name)
4. If valid → creates user + token OR returns existing token (reused=true)
5. Token stored in localStorage on device
6. Same code + same name = same user on any device

**Code is name-assigned**: Each code is pre-assigned to a specific name (Tommy, Hailey, etc). Wrong name = 403 error.

## Activation Codes (name-assigned)

| Code | Assigned To |
|------|------------|
| `ALPWBB36` | Tommy |
| `5KN3WTNX` | Hailey |

Generate more via admin panel (http://18.139.210.59:5001/admin.html) with admin token — each code requires a name assignment.

## Admin Token
```
sbm1Sdkjb0WkUS2iG2FsOHbm_lfSmjDulhZPq3ilhgA
```

## Cloud Sync
User progress stored in VPS DB `users.data` as JSON:
```json
{"wrongIds": [], "totalAnswered": 0, "totalCorrect": 0, "lastUpdated": 1234567890}
```

## Exam Support
Currently: CCSP (default)
Future: CISSP, AAIA — handled by `exam` field in codes/users tables.

## VPS Management

### Connect
```bash
ssh -i "C:/Users/user/PycharmProjects/CryptoStrategy/mcp_server/LightsailDefaultKey-ap-southeast-1.pem" ubuntu@18.139.210.59
```

### Restart Flask app
```bash
systemctl --user restart flask-ccsp
```

### Check status
```bash
systemctl --user status flask-ccsp
```

### View logs
```bash
tail -f /home/ubuntu/ccsp-quiz/flask.log
```

### Open ports (if needed after VPS networking reset)
```bash
aws lightsail put-instance-public-ports --instance-name n8n-trading-bot --port-infos "[{\"protocol\":\"tcp\",\"fromPort\":22,\"toPort\":22,\"cidrs\":[\"0.0.0.0/0\"]},{\"protocol\":\"tcp\",\"fromPort\":5001,\"toPort\":5001,\"cidrs\":[\"0.0.0.0/0\"]}]"
```

## Question Data Pipeline

Source: `C:/Users/user/Downloads/CCSP questionbank.txt` (1.8 MB, space-separated options, no delimiters)

Parsing scripts run in order — each takes `lib/questions.ts` as input and outputs to same file:

1. `vps_api/parse_questions.py` — initial parse from textbank (original, now superseded)
2. `vps_api/rebuild_questions.py` — fixes single-word FRAGMENT options (13 questions)
3. `vps_api/add_full_explanations.py` — replaces truncated explanations with full text (1369 questions)
4. `vps_api/fix_imbalanced_options.py` — fixes options with 3x+ length ratio (697 questions)
5. `vps_api/fix_split_errors.py` — fixes options with `(` or lowercase start (501 questions)

Each script creates a timestamped backup (`lib/questions_pre_*.ts`) before writing.

**Known remaining issues**: ~104 questions where CA anchor failed; options reconstructed via equal-word-count fallback — may be inaccurate. Q1328 option D inferred from CCSP knowledge (textbank missing).

**Root cause of all issues**: textbank stores options as concatenated space-separated words with no delimiter. Parser must infer split boundaries from the correct-answer phrase (CA anchor algorithm).

## Worklog

### 2026-04-05 — Option Split Error Fix (Passes 2 & 3)

**Problem**: After imbalance fix, ~600 more questions still had wrong options:
- Options starting with `(` e.g. `"(CSP) Cloud Service Broker"` — fragment of previous option
- Options starting with lowercase e.g. `"monitoring Contextual-based security"` — split mid-phrase
- Near-equal length options with wrong split point (Q4: Cloud Service roles)

**Fix** (two passes):
- `fix_imbalanced_options.py`: targets length ratio > 3x, 697 fixed
- `fix_split_errors.py`: targets `(`-start or lowercase-start options, 501 fixed; added secondary tie-break (prefer CA option length ≈ CA phrase length to avoid over-splitting)
- Manual patch: Q4 (Cloud Service Partner/Customer/Provider/Broker), Q1328 (contractual terms — inferred missing 4th option as "Regulatory Compliance")

**Deploy**: `50636fa` ✓ https://ccsp-quiz.vercel.app

### 2026-04-05 — Full Explanations Extracted from Textbank

**Problem**: All 1438 questions had truncated explanations. Parser used `([^.]+)` regex stopping at first period, giving only the answer phrase (e.g. "It defines how the data is organized" with no context).

**Fix** (`vps_api/add_full_explanations.py`):
- Extracts full explanation from each textbank block: everything after `Explanation: Correct answer:` until end of block
- Strips trailing reference lines `(ISC)2 CCSP... Pg X`
- Matches by `qtext[:80]` key, updates only when textbank version is longer

**Results**: 1369 updated (avg 3-5x longer), 63 kept (same/shorter), 6 no match
**Backup**: `lib/questions_pre_fullexpl.ts`
**Deploy**: b129aef ✓ https://ccsp-quiz.vercel.app

### 2026-04-03 (later) — Fix All Question Options (Final)

**Problem**: ~47% of questions had corrupted options from pipe-delimiter parser failing on space-separated textbank.

**Root Cause**: Original `parse_questions.py` used `split('|')` which worked when pipe existed, failed silently when it didn't — causing multi-word options to merge into single strings with single-word "fragments" like "are", "they", "must".

**Fix approach** (`vps_api/rebuild_questions.py`):
- Textbank `CCSP questionbank.txt`: 1477 blocks matched to 1438 source questions by first 80 chars of question text
- Only rebuilds questions with FRAGMENT issues (single-word options like "are", "they", "must", "very", etc.)
- CA anchor algorithm finds correct answer phrase in textbank words, uses it to determine split boundaries
- When CA anchor fails, falls back to equal partition

**Algorithm details**:
- `ca_anchor_split`: finds positions where CA phrase appears in merged word list, tries all splits where that position starts the correct option, picks most balanced split with larger s1 preference
- `FRAGMENTS` set: common single words that shouldn't be standalone options
- `has_fragment`: checks if any option is a single FRAGMENT word

**Results** (2026-04-03 final):
- 1425 unchanged (already clean, no fragment issues)
- 13 fixed (corrupted options reconstructed using CA anchor)
- 0 failed (all fixed successfully)

**Key fixes verified**:
- Q79 (zero-trust): Options now correct: ["Monitoring all egress traffic", "Using cryptographic erase", "Continually verifying requests for resources", "Implementing network security groups"]
- Q1354 (PMF payment processor): Options now correct: ["Collection and creation", "Disclosure to third parties", "Monitoring and enforcement", "Security for privacy"]
- Q1207/Q1208: Vendor management and forensic data collection options now correct

**Files changed**:
- `vps_api/rebuild_questions.py` — CA anchor algorithm with tie-breaking (prefer larger s1 for natural boundaries)
- `lib/questions.ts` — replaced with fixed version (1438 questions, same count)
- `lib/questions_backup.ts` — backup of pre-fix version

**Deploy**: `npx vercel --prod --yes` ✓ (https://ccsp-quiz.vercel.app)

### 2026-04-03 (later) — Option Display Fix + fetchCloudData Bug

**Bug 1 — wrongIds always empty (fetchCloudData never ran)**:
VPS `/api/data` returns `{"data": "{\"wrongIds\":[...]}", ...}` — `json.data` is a JSON STRING not a parsed object.
`json.data ?? json` returned the string, `typeof string.wrongIds === 'undefined'`, always returned null.
Fix: added `JSON.parse(data)` when `json.data` is a string.

**Bug 2 — Option display shuffled (47% of questions affected)**:
Textbank (`CCSP questionbank.txt`) has options separated by SINGLE SPACES (no pipe `|` delimiter).
Original parser used `split('|')` — worked when pipe existed, failed silently when it didn't.
Result: multi-word options like "Security Function" got split into "Security" + "Function" as separate options.

**Fixed questions**:
- Q718 (NIST SP 800-53, answer=A): options now ["Separation of System and User Functionality", "Security Function", "Isolation Boundary Protection", "Cryptographic Key Establishment and Management"]
- Q719 (log collection, answer=C): options now ["Logging only administrative account activities", "Storing log files on remote systems until needed", "Aggregating remote logs to a central system", "Filtering logs to collect only high-severity events"]

**Note**: ~47% of questions (699/1483) have merged/split options due to this parsing issue.
Questions with all-single-word options (e.g. Q1, Q3) parsed correctly.

### 2026-04-03 (later) — Login Simplify + Review All Feature

**Problem**:
1. Login required entering name manually — should be automatic (code already assigned to name)
2. No way to review all wrong answers in one go

**Solution**:

Login now only requires code:
- Register API changed to accept `{code}` only — name is looked up from code's assignment
- Frontend login screen: removed name input, just code
- VPS returns `name` in register response for display

Review All feature:
- Added `review` mode to store (`QuizMode = 'login' | 'home' | 'quiz' | 'done' | 'review'`)
- `goReview()` — queues ALL wrong questions sorted by ID, no shuffle, no session limit
- `reviewAnswer()` — doesn't update wrongIds (review mode only)
- `reviewNext()` — advances through review queue, returns to home when done
- Home screen: "Review All" + "Practice" buttons on wrong-questions card
- ReviewScreen: auto-shows explanation immediately after answering, progress indicator "3 / 12"

**Files changed**:
- `vps_api/app_new.py` — register returns name, no name validation needed
- `lib/cloud-sync.ts` — register(code) only, getName() added
- `lib/quiz-store.ts` — review mode, goReview/reviewAnswer/reviewNext
- `app/page.tsx` — removed name from LoginScreen, added ReviewScreen
- `app/api/register/route.ts` — removed name from request body

### 2026-04-03 (later) — Name-Assigned Codes

**Problem**: Each code should map to a specific named user. Tommy using Hailey's code should not work.

**Solution**:
- `codes` table: added `name` column
- `users` table: added `name` column
- Register now requires `{code, name}` — validates name matches code's assigned name before authenticating
- Frontend login screen: added name input field (above code field)
- Admin panel: generate codes requires name input, shows name in codes list

**Files changed**:
- `vps_api/app_new.py` — backend logic
- `vps_api/admin.html` — name input on codes tab
- `lib/cloud-sync.ts` — register(name) added
- `lib/quiz-store.ts` — doRegister(code, name)
- `app/page.tsx` — login screen with name field
- `app/api/register/route.ts` — passes name through

**Database migration on VPS**:
```python
db.execute("ALTER TABLE codes ADD COLUMN name TEXT NOT NULL DEFAULT ''")
db.execute("ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT ''")
db.execute("UPDATE codes SET name = 'Tommy' WHERE code = 'ALPWBB36'")
db.execute("UPDATE codes SET name = 'Hailey' WHERE code = '5KN3WTNX'")
```

**Tested**:
- `ALPWBB36` + Tommy → reused=true (existing token returned)
- `ALPWBB36` + Hailey → 403 "Code not assigned to this name"
- `5KN3WTNX` + Hailey → reused=true

### 2026-04-03 — Setup, Cloud Sync, Multi-User, Codes System

**Problem**: SSH to VPS timed out — port 22 closed after VPS reboot.

**Solution**: Used AWS Lightsail CLI to reopen ports:
```bash
aws lightsail put-instance-public-ports --instance-name n8n-trading-bot --port-infos "[{\"protocol\":\"tcp\",\"fromPort\":22,\"toPort\":22,\"cidrs\":[\"0.0.0.0/0\"]},...]"
```

**Problem**: Flask app not running after VPS reboot — no auto-start.

**Solution**: Created systemd user service at `~/.config/systemd/user/flask-ccsp.service`:
```ini
[Unit]
Description=CCSP Quiz Flask API
After=network.target
[Service]
Type=simple
WorkingDirectory=/home/ubuntu/ccsp-quiz
ExecStart=/usr/bin/python3 /home/ubuntu/ccsp-quiz/app.py
Restart=always
RestartSec=5
[Install]
WantedBy=default.target
```
Enabled with `loginctl enable-linger ubuntu && systemctl --user enable flask-ccsp`.

**Problem**: `send_from_directory` from Flask not working for `/admin.html` route — route registered but returned 404.

**Solution**: Replaced with `send_file` with absolute path:
```python
return send_file("/home/ubuntu/ccsp-quiz/admin.html", mimetype="text/html")
```
Rewrote full `app.py` locally and scp'd to VPS.

**Final State**:
- Flask app running as systemd user service (auto-restart on crash/reboot)
- Admin panel accessible at http://18.139.210.59:5001/admin.html
- 2 activation codes active: ALPWBB36, 5KN3WTNX
- Admin token: `sbm1Sdkjb0WkUS2iG2FsOHbm_lfSmjDulhZPq3ilhgA`

### 2026-04-02 — Initial Setup

- Deployed Next.js app to Vercel
- Set up Flask API on VPS at port 5001
- Parsed 1483 questions from CCSP textbank
- Implemented reusable code system (same code = same user/account)
- Set up Vercel API routes as proxy to bypass CORS
