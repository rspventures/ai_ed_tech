# AI Tutor Platform — 2026 Refactor & Modernization Plan

> **Generated:** 2026-07-04 · **Basis:** full codebase audit (4 parallel analysis agents over `backend/`, `frontend/`, `mobile-app/`) + web research verified against primary sources in July 2026 (Expo/RN changelogs, LangChain/LangGraph releases, provider pricing pages, DPDP/COPPA texts, learning-science RCTs).
> **Audience:** a coding agent (or team of agents) implementing this plan, supervised by the product owner.
> **Scope:** the entire `ai_ed_tech` monorepo — FastAPI backend, React web frontend, Expo mobile app.

---

## 0. How to use this document

- The plan is organized as **4 workstreams** (P = Product/UX, U = UI revamp, T = Tech stack, A = Agentic) plus a cross-cutting **S = Security/Compliance** stream, sequenced into **Phases 0–6** (§8).
- **Work phase-by-phase.** Each phase has explicit exit criteria. Do not start a phase before its predecessor's exit criteria pass (exceptions are noted).
- Every task references audit findings as `file:line` (as of commit `6f63699b` on branch `feature/sarvam-voice`). Verify line numbers before editing — the audit is point-in-time.
- Version numbers in Appendix A were verified against primary sources on 2026-07-04. At implementation time, take the then-latest **stable** patch of the same major/minor unless noted.
- Follow repo conventions in `INSTRUCTIONS.md` **except where this plan explicitly supersedes it** (it supersedes: agent architecture §6, safety pipeline internals §6.5, migration process §5.3, "V1 lesson" content model, and the dual Jaeger+Langfuse observability mandate).
- Update `README.md` / `INSTRUCTIONS.md` as features change (that rule stands).

---

## 1. Current state (audit summary)

### 1.1 What the product is today

K-12 AI tutor for India (CBSE grades 1–7: Maths, Science, English), three clients against one FastAPI backend:

| Capability | Backend | Web (`frontend/`) | Mobile (`mobile-app/`) |
|---|---|---|---|
| Auth (parent account + student profiles) | ✅ JWT + refresh | ✅ | ✅ (but forced re-login every launch) |
| Curriculum browse (Subject→Topic→Subtopic, grade-filtered) | ✅ | ✅ | ✅ |
| AI lessons — V1 text | ✅ (disabled, HTTP 426) | dead code | ✅ **still the only lesson UI** |
| AI lessons — V2 interactive module playlist | ✅ (LLM-gen + cached) | ✅ | ❌ |
| Practice (infinite AI questions, hints, server-graded) | ✅ | ✅ | ✅ |
| Assessment (untimed, AI feedback) | ✅ | ✅ | ✅ |
| Topic test (timed 10Q) / Subject exam (timed, multi-topic) | ✅ | ✅ | ✅ |
| Flashcards + spaced repetition (SM-2-ish) | ✅ | ✅ (Smart Review — broken nav) | built but **unreachable** |
| Favorites / Quick Review of lesson modules | ✅ | ✅ | ❌ |
| Text tutor chat "Professor Sage" (+ vision upload) | ✅ | ✅ | ❌ |
| Voice tutor (WS, ElevenLabs STT/TTS, 10-12 Indic langs detected) | ✅ | ✅ (Sarvam-era code) | ✅ (mic permission missing) |
| Document upload + RAG chat + doc quiz | ✅ | ✅ | ✅ |
| Visual explainer (DALL-E 3) | ✅ | ✅ | ❌ |
| Gamification (XP, levels, streaks) | ✅ | ✅ | ❌ |
| Parent dashboard | ✅ | ✅ | ❌ |
| Teacher/admin | DB tables only (Phase 4 models) | ❌ | ❌ |

### 1.2 Architecture as-built

```
[Expo SDK 50 mobile]   [React 18 + Vite web]
        └──── axios, duplicated types/services (~85% copy-paste) ────┘
                             │ /api/v1 (~70 endpoints)
        FastAPI 0.109 (Jan-2024 pins) · uvicorn --reload · single worker
        ├── Custom BaseAgent (plan/execute) singletons ×17 (5 dead)
        ├── LLMClient → gpt-4o-mini (Anthropic path: retired model ID)
        ├── SafetyPipeline (Presidio PII + injection + blocklists) ×2 overlapping stacks
        ├── RAG: pgvector 0.2.4 + rank-bm25 (rebuilt per query!) + Cohere rerank (sync)
        └── 12 docker containers: postgres+pgvector, redis, neo4j (EMPTY),
            phoenix (DEAD), jaeger, clickhouse+minio+redis+worker+web (Langfuse v3),
            backend, frontend (runs Vite DEV server)
```

### 1.3 Critical defects found (fix in Phase 0)

| # | Defect | Evidence | Impact |
|---|---|---|---|
| D1 | **Assessment integrity broken end-to-end**: examiner prompt mandates *"CORRECT answer must be the FIRST option"* (`backend/app/ai/agents/examiner.py:175-229`); mobile never shuffles options and treats `options[0]` as correct (`mobile-app/app/test/[slug].tsx:339`, `exam/[slug].tsx:450`); server grades against a **client-supplied** `correct_answer` (`backend/app/api/v1/assessment.py:155`, `exam.py:187`, `test.py:209`) | Scores/XP trivially forgeable; tests gameable by always picking A |
| D2 | **Every document upload processes twice** — full extract→OCR→chunk→embed→summarize runs 2× (`backend/app/services/document.py:493` then `:504`) | 2× LLM+embedding cost & latency per upload |
| D3 | RAG document-relevance pre-check **never runs**: `RELEVANCE_CHECK_PROMPT` defined twice, second shadows first → `.format()` KeyError swallowed (`backend/app/ai/agents/rag.py:119,161,892,915`) | Silent quality degradation |
| D4 | Voice text-mode crashes: `sarvam` / `SarvamAPIError` referenced but not imported after ElevenLabs migration (`backend/app/api/v1/voice.py:336,349`) | Typed voice input always errors |
| D5 | Security posture: default `SECRET_KEY` (`backend/app/core/config.py:31`, `docker-compose.yml:253`), `DEBUG=true` + CORS `*` with credentials shipped (`docker-compose.yml:245,254`; `main.py:88`), **no rate limiting on any route incl. paid AI endpoints**, `ai-tutor-key.pem` + `.env` in repo tree with `.gitignore` not covering `.env` | Auth forgery, cost abuse, secret leakage |
| D6 | Practice session state in module-level dicts (`backend/app/api/v1/practice.py:71-82`) | Breaks with >1 worker; memory leak |
| D7 | Mobile forces re-login every launch by design (`mobile-app/src/context/AuthContext.tsx:26-30`); 401-refresh interceptor lacks `_retry` guard and its `SESSION_EXPIRED` signal is never consumed (`src/api/client.ts:41-64`) | Biggest UX friction + stranded sessions |
| D8 | Mic permission not declared (`mobile-app/app.json` → `android.permissions: []`, no iOS `infoPlist`) though voice is a flagship feature | Voice broken on production builds |
| D9 | Retired Anthropic model default `claude-3-sonnet-20240229` (`backend/app/core/config.py:78`) | Anthropic path 404s |
| D10 | Langfuse can silently self-disable (v2-style SDK code + `langfuse>=2.0.0` float pin → v3 SDK import fails → `LANGFUSE_AVAILABLE=False`, `backend/app/ai/core/observability.py:16,81-133`); no API response returns `trace_id`, so the `/feedback` scoring loop cannot attach | Observability black hole |
| D11 | Test suites can't run: backend `conftest.py:20` uses SQLite against Postgres-only JSONB/UUID/Vector models; web has vitest wired, zero tests; mobile has nothing | No safety net |
| D12 | Web Smart Review CTA navigates to non-existent routes (`frontend/src/components/SmartReviewCard.tsx:158,200`); dashboard reads non-existent `feedback.overall_assessment` (`DashboardPage.tsx:602`) | Flagship dashboard features dead-end |

### 1.4 Dormant/dead subsystem inventory (the "subtraction list")

Six shipped-but-inert subsystems create most of the maintenance drag. **Decision: delete in Phase 2** (details §6.1, full file list Appendix C):

1. **LangGraph graphs** — `document_graph.py`, `rag_graph.py` compiled but never invoked; `rag_graph.py` imports nonexistent `get_llm/LLMType` (`:236,267,339`). *(We still adopt LangGraph 1.x — but fresh, not these.)*
2. **Neo4j GraphRAG** — full `GraphStore` client + docker container; the only writer (EntityExtractorAgent) is called solely from the dormant graph → **the graph database is empty in production**. RAG boost degrades to no-op (`rag.py:678-679`).
3. **Arize Phoenix / OpenInference** — `phoenix_metrics.py` referenced by nothing, imports are wrong anyway; container idles.
4. **Celery** — pinned in two manifests; no app, no worker, no task anywhere. Background work = in-process `BackgroundTasks`.
5. **Sarvam + OpenAI-TTS services** — `services/sarvam.py` (362 lines), `services/openai_tts.py` fully unreferenced post-ElevenLabs.
6. **Legacy AI layer** — `agents/tutor.py` (never adopted; `/chat/ask` uses `tutor_chat.py`), `analyzer.py`, `gamification.py` agents, 5 pre-agentic `app/ai/*.py` generator modules imported only by `__init__`. Professor Sage prompt duplicated 3×.

Also dead: mobile `App.js`, orphan flashcards route, web `LessonView.tsx` V1, `react-confetti.d.ts`, unused deps (cva/clsx/tailwind-merge/@tanstack/react-query on web), `require_role` RBAC (defined, used by zero endpoints), `audit_log.py` + `data_retention.py` services (never wired — and retention targets the wrong table `agent_memory`, `data_retention.py:66`).

### 1.5 Key structural problems

- **~85% duplication** between `frontend/src/{services,types}` and `mobile-app/src/{services,types.ts}` — hand-maintained, already drifted (web has V2 lessons/chat/parent/gamification types; mobile doesn't).
- Mobile: no component library (5 bespoke quiz engines, 4 results screens, 2 clashing palettes), no theming, zero accessibility, `ScrollView+.map()` everywhere, no caching layer, no route protection beyond `/`.
- Backend: no Alembic (schema = `create_all` + hand-run SQL 07–12), N+1 queries on hot paths (`learning_path.py:143-206`, `analytics.py:116`), unbounded history/favorites endpoints, `get_current_student` = first child only (`deps.py:105`) — multi-child accounts unsupported.
- No streaming anywhere in the AI stack; JSON extracted by markdown-fence stripping (`llm.py:236-248`); `LLM_MAX_RETRIES` config never referenced; no evals of any kind.

---

## 2. Target end-state

### 2.1 Vision (one paragraph)

A **mobile-first, evidence-based AI tutor for CBSE grades 1–7** that parents trust and kids love: a single warm mascot-led experience with mastery-based learning paths aligned to the new NCERT (NCF-SE 2023) syllabus, a Socratic tutor that provably *doesn't leak answers* and knows each child's mastery history, one unified daily smart session (FSRS reviews + interleaved practice + one new concept), voice tutoring in English/Hindi/Hinglish with a hard safety checkpoint before any audio is spoken, a WhatsApp-first parent loop, and DPDP-compliant child onboarding — running on a right-sized stack (one Postgres, ~6 containers) at ~$0.25–0.50/student/month in model costs.

### 2.2 Target architecture

```
apps/mobile (Expo SDK 57, RN 0.86, React 19.2)          apps/web (Vite 7, React 19)
  NativeWind 4 + RN Reusables · Reanimated 4              student features sunset → parent/
  TanStack Query 5 + MMKV persist · zustand 5             teacher portal (Tailwind 4, TanStack)
  Vercel AI SDK 7 (useChat/SSE) · LiveKit RN (voice)
        └────────────── packages/core (types · zod schemas · API client factory · constants) ──────────────┘
                                   │ REST + SSE + WebRTC (LiveKit)
backend/ (FastAPI latest, Python 3.12, uv, Alembic)
  ├── api: versioned routers + slowapi rate limits + pagination + RBAC (require_role finally used)
  ├── agents/ (LangGraph 1.2.x):
  │     tutor_agent  = create_agent(tools=[search_curriculum, get_mastery, make_visual, lookup_quiz])
  │                    + AsyncPostgresSaver checkpointing + safety middleware (in/out)
  │     workflows/   = deterministic structured-output subgraphs: lesson_gen, quiz_gen,
  │                    feedback_gen, doc_ingest (arq job), flashcard_gen
  ├── llm: LiteLLM router (tiered models, budgets, fallbacks, caching) · structured outputs everywhere
  ├── rag: pgvector 0.8.4 (halfvec + iterative scans) + Postgres-native BM25 + RRF in SQL
  │        + contextualized embeddings + Cohere rerank (async) — exposed as ONE tool
  ├── safety: single pipeline — Presidio(+GLiNER, Aadhaar/PAN) → PromptGuard-class jailbreak
  │        → omni-moderation (in & sentence-buffered out) → grade-band policy · doc-chunk sanitation
  ├── voice: LiveKit Agents worker (Mumbai) — STT(Deepgram Flux multi/Scribe v2) → tutor_agent
  │        → safety gate → TTS (ElevenLabs Flash / Sarvam Bulbul) · barge-in · semantic turns
  ├── jobs: arq (Redis) — doc ingest, WhatsApp digests, retention cleanup, FSRS scheduling
  └── obs: Langfuse SDK v4 (self-hosted v3 platform) = traces+prompts+evals+cost · OTel GenAI conv
             DeepEval in CI (answer-leakage, Socratic quality, safety regression, quiz correctness)

infra: postgres(+pgvector+pg_search) · redis · langfuse stack · backend · web  [neo4j, phoenix, jaeger REMOVED]
```

### 2.3 Headline decisions

| # | Decision | Rationale (details in linked section) |
|---|---|---|
| K1 | **Keep FastAPI + Postgres; upgrade in place.** No framework rewrite. | Backend bones are fine; problems are pins, bugs, and dormant weight (§5.3) |
| K2 | **Mobile: fresh Expo SDK 57 scaffold; port features screen-by-screen.** Not 7 sequential SDK upgrades. | Crosses New-Arch mandatory, React 19, expo-av removal, router rewrite; app has no tests and UI is being revamped anyway; SDK 50 violates Play Store 16KB-page + API-36 (Aug 31, 2026) requirements (§5.2) |
| K3 | **UI: NativeWind 4 + React Native Reusables + Reanimated 4 + Rive mascot.** | Stable, huge community, shadcn-style accessible primitives, web-compatible; NativeWind v5 still preview — do not use (§4) |
| K4 | **Agents: upgrade to LangGraph 1.2.x / LangChain 1.3.x; single tutor-agent + tools; deterministic subgraphs for generation.** Retire the custom BaseAgent gradually. | 0.2.x graph code carries over; middleware gives HIL/PII/summarization; multi-agent supervisor burns ~15× tokens for no pedagogical gain (§6.1–6.2) |
| K5 | **Delete Neo4j/GraphRAG, Phoenix, Jaeger, Celery pin, Sarvam/OpenAI-TTS, legacy agents, dormant graphs.** | All inert (§1.4); curriculum hierarchy is metadata filters, not a graph; Langfuse ingests OTLP so one backend suffices (§6.7) |
| K6 | **Model routing via self-hosted LiteLLM; tiered models; batch for offline gen.** Minors policy constraint: **Gemini only via Vertex AI** (Developer API ToS bans under-18-directed apps) — default tiers on OpenAI minis + Anthropic, Gemini/Vertex optional. | ~$0.20–0.50/student/mo achievable (§6.3, Appendix B) |
| K7 | **Voice 2.0: cascaded STT→agent→TTS on LiveKit Agents (Mumbai), replacing raw record-then-send WS.** | Deterministic safety checkpoint before audio; 3–10× cheaper than S2S; Hindi; barge-in; maintained Expo SDK (§6.6) |
| K8 | **Server-authoritative assessment**: persist questions+keys, grade by question ID, shuffle server-side. | Fixes D1 permanently (§3.1) |
| K9 | **Monorepo: pnpm workspaces + `packages/core`** shared types/API client; backend stays Python with `uv` + single `pyproject.toml`. | Kills the 85% duplication; web stays for parent/teacher surfaces (§5.1, §4.8) |
| K10 | **Observability/evals consolidate on Langfuse (platform already v3) + DeepEval in CI.** Prompts move to Langfuse prompt management. | §6.7 |
| K11 | **Web app pivots to Parent/Teacher portal; the student experience becomes mobile-first.** Student web kept read-only/minimal until sunset decision. | Web duplicates the student app poorly; parent/teacher features are web-natural; INSTRUCTIONS.md "both platforms" rule is retired in favor of per-persona surfaces (§4.8) |
| K12 | **Compliance program to DPDP Rules (India, child = under 18) + amended COPPA now**, shipped before enforcement (13 May 2027). | ₹200cr exposure; voice = biometric under COPPA 2025 (§7) |

---

## 3. Workstream P — Product & UX improvement plan

Evidence base: Khanmigo A/B results (15M+ threads), PNAS guardrails RCT, ASER 2024, Harvard/Stanford/World-Bank RCTs, FSRS benchmarks, Duolingo mechanics data, India market analyses. Each item lists **spec → acceptance criteria (AC) → effort (S/M/L)**.

### 3.1 P0 — Integrity & trust foundations (Phase 0–1)

**P0.1 Server-authoritative assessments (fixes D1).**
- New tables: `question_instances` (id, session_id, subtopic_id, stem, options JSONB *shuffled server-side*, correct_index, misconception_tags JSONB, difficulty, created_at) — questions persisted at generation time for practice/assessment/test/exam/doc-quiz.
- Examiner prompt: remove "correct answer first" instruction; emit `{stem, options[], correct_index, misconception_per_distractor}` via **structured outputs** (§6.3).
- Submit APIs take `{question_id, selected_index}` only; server grades, never trusts client keys; clients never receive `correct_index` until after submission (response includes it for review UI).
- Verify arithmetic deterministically before serving (sympy/eval harness for numeric items) — Khanmigo's accuracy fix pattern.
- AC: e2e test proves a tampered submit cannot score; mobile/web updated; old endpoints return 410 after migration window.
- Effort: **M** (backend S-M, both clients S).

**P0.2 Anti-crutch guardrails ("won't do it for you").**
- Hint ladder policy engine: attempt required before hint 1; hints escalate (nudge → strategy → worked-example-style partial); during active practice/assessment the tutor **never outputs the final answer** (post-assessment review may).
- DeepEval CI suite: answer-leakage red-team prompts per grade band (students adversarially extract answers — treat as jailbreak class); Socratic-quality G-Eval rubric.
- Rationale: PNAS RCT — unguardrailed access **−17% on unaided exams**; guardrailed tutor eliminated harm. This is also the positioning moat vs free ChatGPT/Gemini study modes.
- AC: leakage suite ≥98% pass; visible product copy ("I'll help you think, not give answers").
- Effort: **S–M**.

**P0.3 Persistent login + session recovery (fixes D7).**
- Store tokens in `expo-secure-store`; silent refresh; biometric/PIN optional child-lock instead of forced re-login; global 401 → auth gate redirect (consume the `SESSION_EXPIRED` contract); `_retry` flag on refresh.
- AC: kill app → reopen → still signed in; expired refresh → clean redirect to login.
- Effort: **S**.

### 3.2 P1 — Pedagogy core (Phase 4)

**P1.1 Tutor context injection (Khanmigo's proven +6.1%).**
- Build `learner_model` service: per-student rolling summary — last N attempts (item, correct?, misconception tags), per-subtopic mastery, unmastered prerequisites, preferred language, grade.
- Inject a compact context block into every tutor chat/voice prompt; before hard items, surface a 1-2 line prerequisite refresher.
- AC: context block present in traces; A/B hook ready (prompt version label); next-item-correctness metric logged (§10).
- Effort: **S–M** (data already exists in `progress`; this is aggregation + prompt plumbing).

**P1.2 Mastery map + catch-up mode ("teach at the right level").**
- Prerequisite graph over subtopics (authored JSON per subject/grade — LLM-drafted, human-reviewed; stored as `subtopic_prerequisites` table; NOT Neo4j).
- Placement diagnostic (adaptive ~15 items) locates the child's actual level, possibly below enrolled grade (ASER: only 30.7% of Class 5 can divide); generates a remediation path interleaved with grade-level work; parent-visible "learning level vs grade" framing (sensitively worded).
- India driver: no-detention policy scrapped for classes 5/8 → diagnosis + catch-up is purchase-critical.
- AC: diagnostic produces a path; "Up Next" recommendation consumes it; remediation items tagged in analytics.
- Effort: **L**.

**P1.3 One unified Daily Smart Session (replaces 5 scattered modes as the *default* entry).**
- 10–15 min quest: due FSRS reviews + interleaved mixed-topic retrieval + 1 new concept + celebration close with an explicit "great stopping point".
- **Upgrade SM-2-ish reviewer to FSRS** (open-source `py-fsrs`): ~20–30% fewer reviews for equal retention; unify flashcards + subtopic review into one due-queue.
- Practice/test/exam remain as secondary explicit modes.
- AC: FSRS scheduler behind `review/daily`; session completion event; D7 retention instrumented.
- Effort: **S** (scheduler) + **M** (session UX).

**P1.4 Blend Socratic with worked examples for grades 1–4.**
- Per-grade pedagogy policy in the tutor prompt: younger grades get worked example → faded example → retrieval, not endless question-chains (evidence: worked-example effect for novices; Socratic-only frustrates under-10s).
- Effort: **S** (prompt + eval rubric per band).

**P1.5 Misconception-tagged assessment.**
- Distractors generated with named misconception tags (Eedi pattern) — schema in P0.1; track per-student misconception counts; feed top-3 into tutor context (P1.1); occasionally ask "explain why" even on correct answers (correct-answer-trap mitigation).
- Effort: **M**.

### 3.3 P2 — Engagement layer (Phase 4, after P1 basics)

**P2.1 Mascot & celebration system.** Professor Sage owl becomes a **Rive** character with state machine (idle/thinking/cheering/encouraging); celebration moments at answer/lesson/session levels (confetti via Skia/Lottie); Duolingo-ABC-style audio-forward feedback for grades 1–3.
**P2.2 Kid-safe gamification.** Streaks **with freezes**; XP for effort/mastery milestones (not raw time — DPDP bans behavioral-tracking-style engagement optimization for minors; also motivation-crowding evidence); badges; opt-in, skill-banded weekly leagues later. Surface the existing backend XP/streak (`gamification.py`) in mobile UI at last.
**P2.3 Push/notification policy.** Child-device notifications minimal & study-anchored; streak-at-risk and digest nudges go to the **parent** (P3.2). Effort: P2 total **M**.

### 3.4 P3 — Parent & teacher surfaces (Phase 4–5)

**P3.1 Parent dashboard v2 (web + mobile parent mode).** Minutes, skills mastered, per-subject mastery, weekly trend; **full tutor chat history + moderation alerts** (post-Character.AI, the #1 trust feature); assign practice; session-time controls; multiple children (fix `get_current_student` first-child limitation, `deps.py:105`). Effort: **M**.
**P3.2 WhatsApp parent loop.** Weekly digest, "ask your child today…" micro-prompts, streak-at-risk, exam-countdown, praise certificates; WhatsApp Business Cloud API via arq jobs; deep links back to app. Rationale: the device is often the parent's phone (ASER 84% household smartphone); Rocket Learning precedent. Effort: **M**.
**P3.3 Teacher suite (defer to Phase 6+ / separate initiative).** DB models exist (schools/classes/assignments). Ship only after consumer PMF; roadmap items 4–8 from `roadmap.md` fold in here.

### 3.5 P4 — India market fit (Phase 5–6)

**P4.1 NCERT/NCF-SE 2023 realignment + CBSE competency-based questions.** Re-seed curriculum to the new textbooks (grades 1–8 complete as of 2025-26 — current seed is stale); tag every generated item by competency; add CBQ-style item templates (50% CBQ is the new CBSE pattern cascading down grades). Effort: **M** (content) — high priority, it's a moat window.
**P4.2 Hindi + Hinglish first (then 2–3 regional).** UI i18n (i18next; Devanagari fonts); tutor chat/voice language preference with mid-conversation switching; embeddings/rerank chosen Hindi-capable (§6.4); consider **Bhashini** APIs (govt, 22+ voice languages) and Sarvam Saaras/Bulbul for Indic voice (§6.6); child-voice ASR needs tuning — pilot before promising. Effort: **L** (staged).
**P4.3 Offline-first essentials.** Downloadable lesson packs + flashcards + queued practice for intermittent connectivity (TanStack Query persist + MMKV; content pack format versioned); tutor chat queues gracefully offline. Effort: **M–L** (staged; full sync engine like PowerSync only if multi-device demands it).
**P4.4 Monetization (India-tuned).** Generous free daily loop; premium ₹99–299/mo via **UPI AutoPay**; family plan (2–3 children); exam-season passes; **no big-ticket annual hard-sell** (BYJU'S anti-pattern). Payments via Razorpay/Cashfree. Effort: **M**. *(Owner decision required on pricing — see §12.)*
**P4.5 Trusted-answers UX.** RAG-grounded tutor citations ("Source: NCERT Class 5 Maths, Ch 3"), deterministic math verification, "AI can make mistakes — check with your teacher" low-confidence nudge, visible safety page for parents. Effort: **S–M**.

---

## 4. Workstream U — UI revamp (complete rebuild of the student app)

### 4.1 Design direction

- **Audience split:** Students 6–13 (primary, mobile) · Parents (mobile parent mode + web) · Teachers (web, later).
- **Personality:** warm, playful-but-purposeful; mascot-led (Professor Sage the owl); celebration-rich but with healthy-stop design (AAP-aligned; parents are buyers).
- **Principles:** (1) one design language (kill the two-palette split); (2) age-banded density — grades 1–3 get bigger type/targets, more audio & animation; grades 4–7 get more data/self-direction; (3) light + dark from day 1 (`userInterfaceStyle: "automatic"`); (4) localization-ready (strings externalized, Devanagari-tested layouts); (5) accessibility is not optional (labels, roles, 44×44 targets, dynamic type, reduced-motion).

### 4.2 Design system & tokens (NativeWind theme)

- Tokens in `packages/core/design-tokens` (JSON) → Tailwind config: brand color scale, semantic colors (bg/surface/text/success/warning/danger per light/dark), spacing (4pt grid), radii (friendly, large), type scale (kid-readable rounded face for headings — e.g. Baloo 2 which has excellent Devanagari companion; system font body), elevation, motion durations/easings (Reanimated 4 CSS-style).
- Subject identity colors (Math/Science/English) as tokens, replacing the two hardcoded hex families (`#007AFF`-era and slate-era).
- Dark mode via NativeWind `dark:` variants; per-student accent (`theme_color`) finally honored as an accent token.

### 4.3 Component library (`apps/mobile/src/components/ui` + composites)

Primitives (from RN Reusables, restyled): Button, IconButton, Card, Input, Chip/Badge, ProgressBar/Ring, Sheet/Modal, Tabs, Toast, Skeleton, EmptyState, ErrorState, Avatar, Confetti/Celebration, StreakFlame, XPBar, MasteryRing.
Composites (the deduplication payoff — today these exist ×4–5 bespoke):
- **`<QuizEngine/>`** — ONE engine for practice/assessment/test/exam/doc-quiz: question card, options (single/multi), hint ladder UI, timer variant, navigator dots, submit/confirm flows, per-question feedback, review mode. Config-driven.
- **`<ResultsScreen/>`** — one results composite (score ring, per-topic bars, feedback narrative, actions).
- **`<LessonPlayer/>`** — Lesson V2 module playlist renderer (hook/text/flashcard/quiz/activity/fun-fact/example/summary modules; star-to-favorite; progress).
- **`<ChatThread/>`** — streaming markdown (`react-native-streamdown`), tool-result blocks (inline visuals), suggestion chips, citation chips; used by tutor chat and doc chat.
- **`<VoiceOrb/>`** — LiveKit-driven voice UI: mascot state, live transcript, barge-in, language badge.
- **`<SessionHeader/>`**, **`<SubjectCard/>`**, **`<TopicRow/>`**, **`<DuePill/>`** etc.
- AC: zero screen-local StyleSheet duplication of these patterns; storybook-style gallery screen in dev builds; FlashList v2 for every list; expo-image everywhere.

### 4.4 Navigation & information architecture

expo-router 57 with **typed routes**, native tabs, auth-guarded groups:

```
app/
  (auth)/login.tsx · register.tsx · onboarding/ (parent-first DPDP flow, child profile, placement)
  (student)/                       ← guard: session + selected child
    (tabs)/
      home.tsx        ← Today: daily smart session CTA, streak, up-next, continue-lesson
      learn.tsx       ← subjects → topics → subtopic funnel (grade + mastery aware)
      tutor.tsx       ← chat with Professor Sage (text/vision/voice entry)
      review.tsx      ← due reviews, flashcards, favorites, mistakes notebook
      profile.tsx     ← XP/badges/streak, settings, language, parent-zone entry
    lesson/[subtopicId] · session/[type]/[id] (one quiz route!) · voice.tsx
    documents/ (index + [id] chat)
  (parent)/  ← PIN-gated: dashboard, child mgmt, controls, reports, subscription
```
- Route protection at group `_layout` level (deep links can't bypass — fixes the unguarded `/home` hole); `id` vs `slug` param contract standardized (always ids; slugs only for marketing-visible paths).
- Flashcards become reachable (Review tab) — resolving the orphan feature.

### 4.5 Screen-by-screen revamp map

| Current (17 bespoke screens) | Target |
|---|---|
| `index/login/register` | (auth) group; parent-first onboarding wizard (DPDP consent → child profile → placement diagnostic → personalized home) |
| `home.tsx` (stats + tools + subjects) | **Today** tab: daily session hero, streak/XP header, "continue where you left off", up-next card; subjects move to Learn |
| `subject/[slug]` + `study/[slug]` | **Learn** funnel with mastery map visual (path/journey metaphor), prerequisite-aware locking optional |
| `lesson/[id]` (V1 text) | **LessonPlayer** on Lesson V2 modules (closes web/mobile content gap; V1 path deleted) |
| `practice/assessment/test/exam` (4 engines) | **one `session/[type]` route** on `<QuizEngine/>`; exit-confirm everywhere; auto-submit on timeout; resume-in-progress |
| `flashcards/[topicSlug]` (orphan) | Review tab deck grid + FSRS due queue |
| `voice.tsx` (push-to-talk WS) | `<VoiceOrb/>` full-duplex LiveKit; language picker; parent-visible transcripts |
| `documents/*` | kept, restyled; chat uses `<ChatThread/>`; upload progress states |
| `settings.tsx` | Profile tab + parent-zone (child-safe: no destructive actions without parent PIN) |
| — (new) | Tutor tab (text chat — biggest missing mobile feature), Visual explainer inline in chat (tool call), parent mode screens, offline downloads manager |

### 4.6 States, feedback & long-AI-wait UX

- Every data screen: skeleton → content | empty (illustrated, actionable) | error (retry inline) — standardized via `<AsyncBoundary/>` wrapper over TanStack Query states.
- **Kill the 60–120s blocking spinners**: lesson/quiz generation becomes streamed (§6.3) or precomputed (batch nightly for popular subtopics); where a wait is unavoidable show progress stages ("Reading your document… 3/5") from job status endpoint, with cancel; uploads show background progress with notification on completion.
- Optimistic UI for favorites/completion; pull-to-refresh consistently; offline banners with queued-action affordances.

### 4.7 Accessibility & performance budgets

- a11y: `accessibilityLabel/Role` on all interactive elements; min 44×44 (+`hitSlop`); screen-reader pass per release (Maestro + manual); reduced-motion variants of celebrations; color-contrast AA on both themes.
- Perf budgets (low-end Android, India): cold start < 2.5s on mid-tier; initial AAB install ≤ 30 MB; 60fps lists (FlashList v2); Hermes V1; R8; per-ABI splits; expo-image with explicit sizes; Expo Atlas in CI to watch bundle growth; EAS Update with Hermes bytecode diffing (~75% smaller OTAs — matters on Indian networks).

### 4.8 Web frontend strategy (decision K11)

- **Phase 2–3:** stabilize only — fix D12 dead routes, adopt the shared `packages/core` client/types, actually use TanStack Query (delete hand-rolled fetch state), production Vite build in Docker (current image ships the dev server), remove unused deps, add 404/error boundaries.
- **Phase 4–5:** pivot to **Parent & Teacher portal** (dashboard v2, reports, subscription mgmt, teacher suite later). Student-web features stay functional but frozen; sunset decision after mobile parity (owner call, §12).
- Stack refresh when touched: Vite 7 / React 19 / Tailwind 4 / TanStack Query 5 (used properly) / file or TanStack Router — but **no big-bang web rewrite**; it's not the priority surface.

---

## 5. Workstream T — Technology stack upgrade

### 5.1 Repo & foundations (Phase 1)

1. **Secrets hygiene (with S-stream):** rotate every key present in `.env`/`ai-tutor-key.pem`; purge from git history (`git filter-repo`); `.gitignore` gains `.env`, `*.env.*` (keep `.env.example`), `*.pem`, `deployment.tar.gz`; add `detect-secrets`/gitleaks pre-commit + CI.
2. **Monorepo:** pnpm workspaces — `apps/mobile`, `apps/web`, `packages/core` (zod schemas as single source of truth for API types → both clients; API client factory with injected fetch/storage adapters; shared constants: levels, thresholds, subject colors). Backend can later emit OpenAPI → generate `packages/core/api` types (openapi-ts) so drift is impossible.
3. **Python tooling:** `uv` + single `pyproject.toml` (delete `requirements.txt` divergence — they currently disagree on langchain pins); Python 3.12; ruff + mypy enforced in CI (config exists, unenforced); structured logging (`structlog`) replacing `print()` across the AI layer.
4. **Migrations:** adopt **Alembic** for real (dependency already pinned): baseline autogen from current models; port hand-run SQL 07–12 as the initial revision chain; startup stops calling `create_all`/`run_sql_migrations` (`database.py:60-90`); migrations run via entrypoint `alembic upgrade head`.
5. **CI/CD (GitHub Actions):** backend lint+type+tests (Postgres via testcontainers — fixes D11), web lint+build+vitest, mobile lint+tsc+jest, EAS Build/Update via EAS Workflows on tags; DeepEval suite nightly + on AI-touching PRs.
6. **`get_db` commit-per-request fix** (`database.py:52`): explicit commit in write paths only (or keep autocommit but strip double-commits in services).

### 5.2 Mobile platform (Phase 3) — fresh scaffold, port, revamp

**Why not incremental:** 7 SDK hops (50→57) cross: New Architecture mandatory (Legacy removed in RN 0.82/SDK 55), React 18→19 (PropTypes/defaultProps removal, `react-test-renderer` dead), expo-router 3→57 (React Navigation dropped in SDK 56), **expo-av removed** (SDK 54; voice + any audio must move to expo-audio), expo-file-system API rewrite, edge-to-edge mandatory, ESLint flat config, `expo/fetch` global. With zero tests and a total UI revamp planned, porting into a fresh `create-expo-app` SDK 57 scaffold is faster and safer. **Hard deadline pressure:** Play Store requires target API 36 by **Aug 31, 2026** and 16KB page sizes (in force since Nov 2025) — SDK 50 satisfies neither; SDK 54+ does.

**Target stack (verified 2026-07-04 — Appendix A for full matrix):** Expo SDK 57 (RN 0.86 / React 19.2) · expo-router 57 (typed routes) · NativeWind 4.2 + RN Reusables · Reanimated 4.5 (CSS API; **not Moti** — Reanimated-4 incompatible) · Rive 9.8 + Lottie 7.3 · FlashList 2.3 (+ LegendList 3.3 for chat) · expo-image · TanStack Query 5.101 + persistQueryClient→MMKV · zustand 5 · react-native-mmkv 4.3 (Nitro) · expo-secure-store (tokens) · **drop axios & AsyncStorage** → `expo/fetch` (global, streaming) · Vercel AI SDK 7 (`useChat`) · react-native-streamdown · @livekit/react-native 2.11 + expo-dev-client · expo-audio/expo-video · react-native-keyboard-controller · Jest 30 + jest-expo + RNTL · Maestro E2E on EAS Workflows · ESLint 9 flat + TS 6 strict (`noUncheckedIndexedAccess`) · path aliases (`@/…`) · EAS Update: fingerprint runtimeVersion, 3 channels, staged rollouts.
**app.json fixes rolled in:** mic permission (`android.permissions: [RECORD_AUDIO]` + iOS `NSMicrophoneUsageDescription`), real `apiBaseUrl` per EAS environment, real EAS `projectId`, `userInterfaceStyle: automatic`, edge-to-edge, intentFilters for deep links.

**Porting order:** core plumbing (auth/secure-store/query client) → design system + gallery → auth+onboarding → Today+Learn funnel → QuizEngine sessions → LessonPlayer (V2!) → Review/FSRS → Tutor chat (new) → Documents → Voice 2.0 → parent mode. Old `mobile-app/` stays runnable until parity; new app lives at `apps/mobile`.

### 5.3 Backend platform (Phase 2)

- **Upgrade matrix:** FastAPI 0.109 → latest stable; Pydantic 2.6 → 2.11+; SQLAlchemy 2.0.25 → 2.0.4x; uvicorn latest + **gunicorn/uvicorn-workers, no `--reload`, ≥2 workers** (Dockerfile:36); httpx latest; **python-jose → PyJWT** and **passlib → direct bcrypt/argon2** (both effectively unmaintained); JWT gains `aud`/`iss` validation; `SECRET_KEY` required from env (fail-fast if missing/default).
- **Platform fixes:** slowapi rate limiting (per-IP on `/auth/*`; per-student daily budgets on all AI endpoints — cost abuse is the real risk); pagination (limit/offset + `COUNT`) on the 3 history endpoints, favorites, documents/visuals (totals currently wrong: `documents.py:242`, `visuals.py:184`); batch the N+1s in `learning_path.py`/`analytics.py` into aggregate queries; Redis-backed practice sessions (D6); multi-child: `student_id` param + ownership check pattern from `parent.py:28` applied across routers; wire `require_role` RBAC (teacher/admin ready); TrustedHost + GZip middleware; request-ID logging.
- **Background jobs:** adopt **arq** (Redis-based, async-native, lighter than Celery) — queues: `doc_ingest` (moves ingestion out of web process, survives restarts, retries, progress states), `digests` (WhatsApp/email), `retention` (wire the orphaned data_retention service, pointed at the *correct* tables), `batch_gen` (nightly lesson/quiz precompute via provider Batch APIs). Delete the Celery pin.
- **DB:** pgvector extension 0.2.4 → **0.8.4** (halfvec optional, iterative index scans ON — fixes filtered-query overfiltering), python client 0.4.2; add **ParadeDB `pg_search`** (BM25 in Postgres) replacing `rank_bm25` (currently rebuilt per query, O(corpus)); RRF fusion moves into SQL.
- **Infra:** docker-compose slims 12 → ~7 containers (drop neo4j, phoenix, jaeger); prod compose variant with DEBUG=false, explicit CORS origins, TLS via Caddy/Traefik (or keep nginx + certbot — `setup_nginx.sh` currently plain HTTP); healthchecks for backend; web image does `vite build` + static serve.

### 5.4 Testing strategy (cross-phase, starts Phase 1)

| Layer | Tooling | Priority suites |
|---|---|---|
| Backend unit/API | pytest + pytest-asyncio + **testcontainers-postgres** (replaces broken SQLite fixtures) | auth, grading integrity (P0.1!), practice flow, RAG retrieval contract, safety pipeline verdicts, pagination |
| AI quality | **DeepEval** in CI + Langfuse datasets | answer-leakage, Socratic rubric, quiz JSON validity + correctness spot-checks, safety regression (child personas), grounding |
| Mobile | Jest 30 + RNTL; **Maestro** E2E on EAS Workflows | auth flow, daily session happy path, quiz engine (timer, submit, resume), offline lesson open |
| Web | vitest + RTL (finally) | parent dashboard, portal auth |
| Load | k6 smoke on AI endpoints with budget alarms | pre-launch |

---

## 6. Workstream A — Agentic framework optimization

### 6.1 Subtraction first (Phase 2 start; ~3–4k LOC and 3 containers removed)

Delete (full list Appendix C): both dormant LangGraph graphs (rebuild fresh on 1.x — do **not** port `rag_graph.py`, its imports never worked), Neo4j + `graph_store.py` + EntityExtractorAgent + graph-boost branch in `rag.py:652-723`, Phoenix service + deps + container, Celery pins, `services/sarvam.py`, `services/openai_tts.py`, Sarvam/OpenAI-TTS config blocks, `agents/tutor.py` (unused), `analyzer.py`, `gamification.py` agent, the 5 legacy `app/ai/*.py` generator modules + their `__init__` imports, duplicate `guardrails.py` layer inside LLMClient (superseded by unified pipeline §6.5), contextual-retrieval dead flag path (superseded by §6.4), Jaeger + generic OTel exporters (Langfuse becomes the OTLP sink), mock-question fallback pool if keys are now guaranteed (`practice.py:237-317` — keep behind explicit `DEMO_MODE` if wanted).

### 6.2 Framework & topology (Phase 2)

- **LangGraph 1.2.x + LangChain 1.3.x** (GA Oct 2025; current 1.2.7/1.3.11). Migration notes: `create_react_agent`/`langgraph.prebuilt` → `langchain.agents.create_agent`; TypedDict agent state; middleware system replaces bespoke hooks; Python ≥3.10 (we target 3.12). Checkpointing via `langgraph-checkpoint-postgres` 3.1 (durable tutor sessions in the DB we already run — replaces the 1h-TTL Redis `AgentMemory` for chat).
- **Topology: ONE tutor agent + tools; deterministic workflows for generation.** Evidence-based: multi-agent supervisors burn ~15× tokens for no gain here; OpenAI/Anthropic guidance says maximize a single agent first.
  - `tutor_agent = create_agent(model=router("tutor"), tools=[search_curriculum, get_learner_context, make_visual, lookup_quiz_item, request_worked_example], middleware=[safety_in, pii_redact, summarize_history, safety_out], checkpointer=postgres)` — serves text chat, doc chat (tool-scoped to a document), and the voice pipeline's reasoning step.
  - `workflows/` (plain LangGraph subgraphs, structured outputs, no agent loop): `lesson_v2_gen`, `quiz_gen` (emits P0.1 schema), `feedback_gen`, `flashcard_gen`, `doc_ingest` (extract→OCR→chunk→embed→summarize→validate as an arq job — **single-run**, fixing D2), `visual_explain`.
- **BaseAgent retirement:** keep the class as a thin adapter during Phase 2 (safety+tracing now come from middleware); delete once all callers move. `INSTRUCTIONS.md` §1 gets rewritten accordingly.
- Legacy `tutor_chat.py` (the live chat path) is replaced by `tutor_agent` behind the same `/chat/ask` contract + a new SSE streaming variant; the 3 duplicated Professor Sage prompts collapse into one Langfuse-managed prompt with grade-band variants.

### 6.3 LLM layer (Phase 2)

- **LiteLLM proxy (self-hosted)** fronts all model calls: virtual keys per surface, per-student daily budgets (defense-in-depth with slowapi), fallbacks, latency routing, cost telemetry → Langfuse native integration.
- **Structured outputs everywhere** (provider-native json_schema / strict tools) — delete fence-stripping `generate_json` (`llm.py:236-248`). Retries with backoff (finally honoring `LLM_MAX_RETRIES`), circuit breaker, per-call timeouts.
- **Streaming end-to-end:** SSE for `/chat/ask` + doc chat (FastAPI `StreamingResponse` → AI SDK 7 `useChat` on mobile via `expo/fetch`); token-level streaming from LangGraph (`astream`); sentence-buffered through output safety (§6.5).
- **Model tiers** (Appendix B for verified July-2026 prices; re-verify at implementation): default tutor chat on a mini-tier model (e.g. `gpt-5.4-mini`; escalate on difficulty/negative feedback); nano-tier for classification/routing/moderation-adjacent tasks; frontier (Claude Sonnet 5 / GPT-5.5) only for lesson-gen quality passes and rare escalations; **Batch APIs (50% off) for nightly precompute**; prompt caching structured deliberately (stable system+curriculum prefix). **Minors-policy guardrail (K6):** Gemini models ONLY via Vertex AI enterprise terms if used; never the Gemini Developer API (its ToS prohibits under-18-directed services). OpenAI under-18 guidance: zero-data-retention config for under-13 PII; Anthropic minors conditions: disclosure, moderation, COPPA statement — both implemented in §7.
- Embeddings consolidated into **one** cached service (currently instantiated in ≥6 places) — see §6.4 for model choice.

### 6.4 RAG 2.0 — right-sized (Phase 2)

Corpus is modest (uploaded docs + curriculum chapters): one Postgres, no graph DB, no ColPali.

1. **Ingest (arq job, single-run):** parse (pypdf/PyMuPDF; GPT-4o-class vision OCR for scanned pages — through the router, not raw httpx as today `vision_ocr.py:57`); **VLM-caption every figure** and index captions as text chunks; structure-aware chunking 400–800 tok with `grade/subject/chapter/language` metadata columns.
2. **Embeddings:** contextualized-embedding API — **voyage-context-4** (auto-chunking, removes manual contextual-enrichment work) *or* `gemini-embedding-001`-class via Vertex / `text-embedding-3-large` fallback — final pick at implementation after a 1-day bake-off on Hindi+English school content (all candidates Hindi-capable; eval with a 100-query golden set).
3. **Store/search:** pgvector 0.8.4 HNSW (+halfvec optional) with iterative scans; BM25 via ParadeDB `pg_search`; **RRF in SQL**; async Cohere Rerank (3.5 or 4-Fast — Hindi supported) replacing the sync client that blocks the event loop (`reranker.py:78-83`).
4. **Agentic layer:** retrieval exposed as ONE tool `search_curriculum(query, grade, subject, chapter?, language?, document_id?)`; tutor decomposes/re-queries on weak results, **capped at 2–3 iterations**; simple lookups stay one-shot. META/summary queries: keep the summary meta-chunk pattern (it's good) behind the same tool.
5. **Grounding & citations:** replace the lexical grounding check (`rag.py:1021-1025`, near-always true) with span-citation prompting + a DeepEval groundedness metric sampled online; citations surface in UI (P4.5).
6. Sanitize retrieved chunk text before prompt injection (indirect-prompt-injection defense — currently absent, `rag.py:996-1016`).

### 6.5 Safety pipeline 2.0 (Phase 2, hardened Phase 4)

Consolidate the two overlapping stacks (SafetyPipeline + guardrails.py) into **one pipeline as LangChain middleware**, applied to every surface (chat, voice, generation workflows):

- **Input rail (parallel, ~100–300ms):** Presidio upgraded (+GLiNER recognizer; keep/extend Aadhaar/PAN/roll-number custom recognizers — good work, `pii_redactor.py:123-163`) → jailbreak classifier (Prompt-Guard-2-class small model via Groq, or keep the existing 3-layer detector with tuned thresholds) → **OpenAI omni-moderation (free)** → grade-band topic policy (replace the over-blocking regex blocklists that currently kill "die/fight/high/romance" in legitimate K-12 content, `content_moderator.py:53-84`, with allowlist-of-subjects + LLM policy check on ambiguity).
- **Output rail:** sentence-buffered moderation during streaming (omni-moderation or Llama-Guard-4 on Groq); fix-or-refuse policy; the self-critique refinement finally gets a real llm_client (it's currently dead — `safety_pipeline.py:287,394-396`).
- **Escalation:** self-harm/grooming signals → block + human review queue + parent alert path + India helpline (Tele-MANAS 14416) surfaced age-appropriately; all safety verdicts traced to Langfuse and audited (wire the orphaned `audit_log.py`).
- **Anti-crutch enforcement** (P0.2) lives here too: answer-leakage detector on tutor outputs during active assessment contexts.
- Voice uses the **same** rails at the text checkpoint (§6.6). Real grade passed everywhere (voice hardcodes grade=5 today, `voice.py:166`).

### 6.6 Voice 2.0 (Phase 5)

Replace the half-duplex record-then-send WS (`voice.py`, `mobile-app/app/voice.tsx`) with a **cascaded pipeline on LiveKit Agents** (self-host worker or LiveKit Cloud **Mumbai/ap-south**):

- **STT:** Deepgram Flux Multilingual (Hindi, model-based end-of-turn, ~$0.0078/min) or ElevenLabs Scribe v2 Realtime (11 Indic languages, India data residency); evaluate **Sarvam Saaras v3** for deeper Hinglish code-mixing. *(Child-voice accuracy pilot required before launch promise — generic ASR degrades on kids.)*
- **Reasoning:** the same `tutor_agent` (checkpointed session, learner context injected) — voice and text share brains, prompts, and safety.
- **Safety gate:** full §6.5 rails on the transcript BEFORE TTS — the decisive advantage of cascade over speech-to-speech for a kids' product (S2S guardrails are post-hoc and can leak audio; cascade is also 3–10× cheaper: ~$0.03–0.04/min all-in vs $0.08–0.30).
- **TTS:** ElevenLabs Flash (Indian-English/Hindi voices) or **Sarvam Bulbul v3** (Hinglish code-switching, ₹-priced) — streamed, first-sentence-fast.
- **Client:** `@livekit/react-native` + Expo dev-client plugin; barge-in, semantic turn detection (LiveKit turn detector supports Hindi), mascot states, live transcript, parent-visible session transcripts. WS token moves out of query string.
- **Compliance:** raw audio never retained (COPPA 2025 voiceprints=biometric); transcripts stored redacted with retention schedule.
- Optional premium S2S path later via LiveKit's OpenAI plugin (config swap, not rearchitecture).

### 6.7 Observability, prompts & evals (Phase 2, matured Phase 4)

- **Langfuse platform:** already v3 in compose (keep; pin image, set real SALT/ENCRYPTION_KEY/NEXTAUTH_SECRET). **Python SDK v2-style code → SDK v4** (`propagate_attributes`, OTel-based; requires platform ≥3.125 — upgrade image accordingly). LangGraph traced via `CallbackHandler`; LiteLLM callback adds gateway-level costs (replace the hardcoded stale price table, `observability.py:47-60`).
- **Close the feedback loop:** every AI response returns `trace_id`; `/feedback` thumbs attach as Langfuse scores (currently impossible — D10); online LLM-judge sampling on production traces (groundedness, Socratic adherence, tone).
- **Prompt management:** all prompts (one Professor Sage!) into Langfuse with `production`/`staging` labels, SDK-cached, in-code fallbacks; label-based A/B canaries (Khanmigo-style experiments, e.g. context-injection variants); prompt-version ↔ metric linkage.
- **Drop Jaeger + Phoenix** (K5): Langfuse ingests OTLP; keep OTel semconv GenAI spans from the app if useful, exported to Langfuse only. Delete the never-activated httpx/redis/sqlalchemy instrumentation pins or actually activate them → Langfuse.
- **Evals:** DeepEval suites in CI (P0.2 leakage, safety personas, quiz schema+correctness sample, RAG groundedness on a golden set); Langfuse datasets for regression experiments before prompt promotions; weekly eval report artifact.

---

## 7. Workstream S — Security & compliance (cross-cutting)

**Phase 0 (immediate):** rotate + purge secrets (D5); enforce non-default `SECRET_KEY`; `DEBUG=false` outside dev; explicit CORS origins; slowapi on auth + AI routes; TLS termination; `--reload` off + multi-worker; WS auth via first-message token or short-lived ticket (not query param); `aud/iss` JWT claims; bcrypt→argon2id on next password change.

**DPDP program (India — child = under 18; core obligations enforceable 13 May 2027; build in Phase 5–6, design from Phase 1):**
- Parent-first onboarding with **verifiable parental consent** (Rule 10; DigiLocker/virtual-token-ready design), immutable consent audit trail, grievance/DPO contact page.
- **Zero behavioral tracking / no ad SDKs / no engagement-optimized profiling of children** (§9(3), ₹200cr) — audit analytics events; gamification rewards mastery, not usage (aligned in P2.2).
- Data minimization + retention schedules (wire `data_retention.py` correctly via arq; chat 90d default, raw audio never stored, documents per policy) + parent-triggered erasure.
- Data residency preference: Vertex asia-south1 / Bedrock ap-south for models where feasible; self-hosted Langfuse keeps traces in-house.

**COPPA (amended rule fully in force Apr 2026, if US users):** voiceprints=biometric (no raw audio retention), separate consent for third-party disclosure/AI-training, written retention policy. **EU AI Act Art 50** (Aug 2026): clear "you're talking to an AI" disclosure — ship globally, it's also an OpenAI/Anthropic minors condition.
**Vendor conditions:** publish COPPA-compliance + child-safety page (Anthropic requirement); OpenAI under-18 guidance (ZDR for under-13 PII, monitoring, escalation paths); **no Gemini Developer API** (K6).
**Positioning:** "India's most privacy-safe AI tutor" — compliance as marketing, not tax.

---

## 8. Execution roadmap

> Effort assumes a capable coding agent + owner review. Phases 2/3 can run in parallel tracks (backend vs mobile) after Phase 1. Rough calendar: **~14–18 weeks** total.

### Phase 0 — Stop the bleeding (≈1 week) — on current stack, no upgrades
- [ ] S: rotate/purge secrets; `.gitignore` fix; fail-fast SECRET_KEY; DEBUG/CORS prod config; basic slowapi on `/auth/*` + AI endpoints
- [ ] P0.1 backend: persist questions+keys server-side; grade by ID; shuffle options server-side; strip "correct-first" from examiner prompt; minimal client patches (mobile+web) to new submit contract
- [ ] Fix D2 (single ingestion run), D3 (dedupe RELEVANCE_CHECK_PROMPT), D4 (remove sarvam branch), D9 (current Anthropic model ID or disable path), D12 (web dead routes/field)
- [ ] Mobile quick wins (old app, shipped as patch): mic permission in app.json; persistent login (P0.3); exit-confirm on test/exam; option-shuffle rendering
- **Exit:** tampered-submit test fails to score; upload processes once (log/trace proof); voice text path works; secrets scanner green.

### Phase 1 — Foundations (≈1–2 weeks)
- [ ] Monorepo (pnpm) + `packages/core` extraction (types/zod + client factory) consumed by web first
- [ ] uv + pyproject single manifest; ruff/mypy/structlog; Alembic baseline + migration chain; startup migration runner removed
- [ ] CI: backend pytest+testcontainers green (rewrite fixtures — D11), web build+vitest, secret scan, DeepEval skeleton
- [ ] docker-compose: prod/dev split; web prod build; backend gunicorn workers; healthchecks
- **Exit:** CI green on all suites; `alembic upgrade head` from empty DB reproduces schema; one shared type used by both web and (old) mobile client.

### Phase 2 — Backend & agentic modernization (≈3–4 weeks)
- [ ] Subtraction list executed (§6.1, Appendix C); compose 12→~7 containers
- [ ] Dependency upgrade matrix (§5.3); PyJWT/argon2; pagination; N+1 batching; Redis practice state; multi-child + RBAC wiring
- [ ] LangGraph 1.2 + LangChain 1.3; `tutor_agent` + tools + Postgres checkpointer replaces tutor_chat; generation workflows w/ structured outputs; BaseAgent adapters
- [ ] LiteLLM router + tiers + budgets; retries/fallbacks; SSE streaming chat (+web client); batch precompute job for top lessons
- [ ] RAG 2.0 (§6.4): pgvector 0.8.4 + pg_search + SQL RRF + async rerank + embedding bake-off + single embedding service; retrieval-as-tool
- [ ] Safety 2.0 consolidation (§6.5) incl. blocklist→policy replacement + doc-chunk sanitation
- [ ] Langfuse SDK v4 + trace_id loop + prompts migrated; DeepEval CI suites (leakage/safety/quiz/groundedness); arq jobs (ingest/retention)
- **Exit:** all AI traffic through router with per-student budgets; chat streams; eval suites ≥ agreed thresholds; p95 chat first-token < 1.5s; container count reduced; zero references to deleted subsystems.

### Phase 3 — Mobile rebuild (≈3–4 weeks, parallel with late Phase 2)
- [ ] `apps/mobile` fresh Expo SDK 57 scaffold + target stack (§5.2); design tokens + component library + gallery (§4.2–4.3)
- [ ] Auth/onboarding + route groups/guards; Today/Learn/Review/Profile tabs; QuizEngine sessions (server-authoritative contract); LessonPlayer V2; tutor chat tab (AI SDK 7 + streamdown); documents; parent mode shell
- [ ] TanStack Query + MMKV persistence (offline reads); FlashList/expo-image; a11y pass; perf budgets measured in CI (Atlas)
- [ ] Jest+RNTL units for engine/logic; Maestro flows (auth, session, quiz, offline open); EAS build profiles + Update channels + staged rollout
- **Exit:** feature parity with old app **plus** chat/V2 lessons/gamification UI/flashcards reachable; Play Store internal track build (API 36, 16KB) passes; Maestro suite green; old `mobile-app/` frozen.

### Phase 4 — Pedagogy & engagement (≈2–3 weeks)
- [ ] P1.1 context injection + A/B scaffold · P1.3 FSRS + Daily Smart Session · P1.4 grade-band pedagogy prompts · P1.5 misconception tagging · P0.2 hardening iteration against eval results
- [ ] P2 mascot (Rive) + celebrations + streak-freeze/XP rework · P3.1 parent dashboard v2 (web portal + mobile parent mode)
- **Exit:** next-item-correctness + D7 instrumentation live; leakage suite ≥98%; parent can see chat history + alerts.

### Phase 5 — Voice 2.0 + India fit (≈2–3 weeks)
- [ ] LiveKit Agents worker (Mumbai) + mobile VoiceOrb; STT/TTS bake-off incl. child-voice pilot; same safety rails; transcripts to parent view
- [ ] P4.1 NCERT re-seed + CBQ item styles · P4.2 Hindi/Hinglish UI + tutor (staged) · P4.3 offline packs v1 · P3.2 WhatsApp digests
- **Exit:** voice p95 voice-to-voice < 1.5s; Hindi tutor conversation demo; offline lesson demo; first WhatsApp digest delivered.

### Phase 6 — Compliance, monetization & launch (≈2 weeks + ongoing)
- [ ] S: DPDP consent flow + audit trail + retention jobs + policy pages; AI-disclosure UX; safety page
- [ ] P4.4 payments (UPI AutoPay) + plans + paywall UX; k6 load pass; staged Play Store rollout via EAS
- **Exit:** compliance checklist signed off; billing e2e in sandbox; production rollout 1%→100%.

---

## 9. Cost model (verify quotes at implementation; sources July 2026)

- **Tutor chat:** mini-tier (~$0.25–0.75/M in, $1.25–4.50/M out) with cached system prefix → **~$0.20–0.35/student/mo** at ~600K in/90K out tokens.
- **Lesson/quiz precompute:** Batch APIs 50% off → pennies per lesson, amortized by caching (already cached per subtopic+grade).
- **Voice:** cascade ~$0.03–0.04/min all-in (STT $0.006–0.008 + mini-LLM + TTS $0.008–0.02 + LiveKit ~$0.01) vs $0.08–0.30 S2S. 60 min/mo voice ≈ $2 — gate behind premium.
- **RAG:** embeddings $0.02–0.18/M tok one-time per doc; rerank ~$2/1K searches; retrieval infra $0 (in Postgres).
- **Safety:** omni-moderation free; Llama-Guard-4 ~$0.18/M via Groq; Presidio self-hosted.
- **Infra:** single VM + managed Postgres feasible post-slimming; Langfuse self-host ≈ infra-only.
- **Rule of thumb target:** free tier COGS < ₹8/student/mo; premium student all-in < ₹40/mo → healthy at ₹99–299 pricing.

## 10. Success metrics (instrument from Phase 2/3)

Learning: **next-item correctness** (the Khan metric), mastery velocity, diagnostic→remediation completion. Engagement: D1/D7/D30, daily-session completion, streak health (freezes used vs broken). Trust/safety: leakage-eval pass rate, moderation FP rate (over-blocking), parent-alert response time. Quality: thumbs-up rate wired to traces, groundedness score, p95 first-token latency, voice v2v latency. Economics: cost/student/mo by tier, cache-hit rates, budget-cap trips.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Fresh-scaffold mobile port stalls → two apps forever | Freeze old app at Phase 0 patch; port in vertical slices with weekly EAS internal builds; parity checklist in CI |
| LangGraph/LangChain 1.x API drift during port | Pin exact versions; adapter layer around agent invocation; contract tests on `/chat/ask` |
| Model prices/IDs shift (they will) | LiteLLM aliases (`tutor-default`, `gen-batch`…) so swaps are config; re-verify Appendix B quarterly; Sonnet-5 intro pricing ends Aug 31, 2026 |
| Child-voice ASR accuracy in Hindi/Hinglish | Bake-off + pilot with real recordings before marketing voice-Hindi; constrained-vocab fallbacks for grades 1–3 |
| Over-blocking safety harms UX (current blocklists) | Policy-based moderation + FP metric + weekly review queue; grade-band allowlists |
| DPDP consent UX depresses signup | Progressive flow (explore-as-guest → consent at first child profile); DigiLocker later, start with document+OTP grade consent |
| Scope explosion | Phase gates are hard; teacher suite explicitly deferred; §12 decisions owner-only |

## 12. Open questions for the product owner

1. **Pricing/packaging** (P4.4): confirm ₹99–299/mo hypothesis, family-plan size, what's free vs premium (voice minutes? doc uploads?).
2. **Web student experience**: freeze-and-sunset after mobile parity, or maintain? (Plan assumes freeze → parent/teacher portal.)
3. **Grade range**: stay 1–7 or extend to 8 (new NCERT covers 1–8; CBQ pressure is strongest 8–10)?
4. **Languages order** after Hindi/Hinglish (Marathi? Tamil? Telugu? Bengali?).
5. **Voice vendor posture**: OK with ElevenLabs+Deepgram (US processing) vs Sarvam/Bhashini (India-first) as primary?
6. **US market**: any US users planned? (Triggers full COPPA program now vs DPDP-only.)
7. **Team/agent budget**: single coding agent serial, or parallel backend+mobile tracks (plan assumes parallel from Phase 2/3)?

---

## Appendix A — Verified version matrix (2026-07-04)

| Component | Current | Target | Notes |
|---|---|---|---|
| Expo SDK | ~50.0.0 | **57** (RN 0.86, React 19.2) | SDK 54+ = API 36 + 16KB compliant; New Arch mandatory ≥55 |
| expo-router | ~3.4.0 | 57.x | React-Navigation-free since 56; typed routes |
| Styling | StyleSheet | NativeWind 4.2.6 + RN Reusables | v5 preview — do NOT adopt yet |
| Animation | RN Animated | Reanimated 4.5.x + Rive 9.8 + Lottie 7.3 | Moti incompatible with Reanimated 4 |
| Lists/Image | ScrollView+map | FlashList 2.3 / LegendList 3.3 / expo-image 57 | |
| Data | none/axios/AsyncStorage | TanStack Query 5.101 + zustand 5 + MMKV 4.3 + expo-secure-store + expo/fetch | axios & AsyncStorage removed |
| AI chat client | — | Vercel AI SDK 7 (`ai@7.0.x`) + react-native-streamdown 0.2 | streamdown is 0.x — keep markdown-display fallback |
| Voice client | expo-av + raw WS | @livekit/react-native 2.11 + expo-audio | expo-av removed in SDK 54 |
| Mobile testing | none | Jest 30 + RNTL + Maestro (EAS Workflows) | react-test-renderer is dead (React 19) |
| Python | 3.11 | 3.12 + uv | single pyproject |
| FastAPI/Pydantic/SQLAlchemy | 0.109 / 2.6 / 2.0.25 | latest stable at impl. | + gunicorn workers |
| Auth libs | python-jose / passlib+bcrypt | PyJWT / argon2-cffi | jose & passlib unmaintained |
| LangChain / LangGraph | 0.2.x / 0.2.x | **1.3.x / 1.2.x** (+ langgraph-checkpoint-postgres 3.1) | create_agent, middleware, TypedDict state |
| LLM gateway | none | LiteLLM (self-hosted, latest) | budgets, fallbacks, Langfuse callback |
| pgvector | ext 0.2.4 / client 0.2.4 | ext **0.8.4** / client 0.4.2 | halfvec, iterative scans |
| BM25 | rank-bm25 (per-query rebuild) | ParadeDB pg_search (Postgres-native) | RRF in SQL |
| Rerank | Cohere rerank-english-v3.0 (sync) | Cohere Rerank 3.5 / 4-Fast (AsyncClient) | Hindi-capable |
| Embeddings | text-embedding-3-small ×6 call sites | bake-off: voyage-context-4 vs gemini-embedding-001(Vertex) vs OpenAI 3-large — one service | Hindi golden-set eval |
| Jobs | BackgroundTasks (Celery pinned unused) | **arq** | delete Celery |
| Observability | Langfuse v2-SDK(broken-ish)+Jaeger+Phoenix | Langfuse platform v3 (pinned) + **SDK v4**; drop Jaeger/Phoenix | OTLP into Langfuse |
| Evals | none | DeepEval 4.x CI + Langfuse datasets/online judges | leakage/safety/groundedness/quiz |
| PII | Presidio 2.2 (Jan-2024) | Presidio latest + GLiNER; keep India recognizers | |
| Moderation | regex blocklists ×3 | omni-moderation (free) + Prompt-Guard-class + policy LLM | grade-banded |
| Voice backend | raw WS + ElevenLabs turbo | LiveKit Agents 1.6 (Mumbai) cascade | Flux-multilingual/Scribe-v2/Saaras STT · Flash/Bulbul TTS |
| Web | React 18/Vite 5/Tailwind 3 (dev server in prod) | React 19/Vite 7/Tailwind 4 when touched; prod build now | pivot to parent/teacher portal |
| Neo4j / Phoenix / Jaeger | running idle | **removed** | |

## Appendix B — Model routing table (prices verified 2026-07-04; re-verify quarterly)

| Alias | Workload | Primary | Escalation/Notes |
|---|---|---|---|
| `tutor-default` | Socratic chat/voice reasoning | gpt-5.4-mini ($0.75/$4.50) *or* Sonnet-class via Bedrock ap-south | escalate on difficulty/negative feedback → gpt-5.5 / Sonnet 5; Gemini flash-lite ($0.25/$1.50) **only if via Vertex** (minors ToS) |
| `classify-nano` | routing, language detect, misconception tagging | gpt-5.4-nano ($0.20/$1.25) or Haiku 4.5 | temperature 0, structured |
| `gen-batch` | nightly lesson/quiz/flashcard precompute | Claude Sonnet 5 Batch ($1/$5 until 2026-08-31, then $1.50/$7.50) | quality pass sampled by judge |
| `quiz-live` | on-demand quiz JSON | gpt-5.4-mini strict schema | deterministic math verify after |
| `visuals` | educational images | gemini-3.1-flash-image via Vertex (~$0.05/img) or gpt-image-1-mini | replaces DALL-E 3 |
| `judge` | evals/online judges | Haiku 4.5 / gpt-5.4-mini | never the model being judged |
| `moderate` | safety rails | omni-moderation (free) + Llama-Guard-4 (Groq ~$0.18/M) | |

## Appendix C — Deletion list (Phase 2 unless noted)

Backend: `app/ai/graphs/{document_graph.py,rag_graph.py,base.py}` (rebuild fresh) · `app/ai/agents/{entity_extractor.py,tutor.py,analyzer.py,gamification.py}` · `app/ai/{tutor_chat.py (after cutover),question_generator.py,lesson_generator.py,answer_evaluator.py,assessment_analyzer.py,review_agent.py}` · `app/ai/core/guardrails.py` (merge into safety) · `app/services/{sarvam.py,openai_tts.py,graph_store.py,phoenix_metrics.py}` · Celery/neo4j/phoenix/opentelemetry-exporter-jaeger pins · mock-question pool (`practice.py:237-317`, keep behind DEMO_MODE if desired) · unreachable code `study.py:248-258` · V1 lesson endpoint after mobile V2 ships.
Compose: `neo4j`, `phoenix`, `jaeger` services + volumes.
Mobile (old app dies at Phase 3 parity): `App.js` now.
Web: `LessonView.tsx` (V1), `types/react-confetti.d.ts`, unused deps (cva/clsx/tailwind-merge — or start using them in the portal), hand-rolled fetch state after Query adoption.
Root: `deployment.tar.gz`, `ai-tutor-key.pem` (rotate first!), `check_git.bat`, stale `rename_migrations.py`/`restore_migrations.py` after Alembic.

## Appendix D — Key evidence & sources (fetched 2026-07-04)

Learning science: PNAS guardrails RCT (Bastani et al.) · Khan Academy tutor-learnings blog (context injection +6.1%) · Harvard PS2-Pal RCT · Stanford Tutor CoPilot · World Bank Edo/Nigeria · FSRS benchmarks (Anki) · ASER 2024.
Frameworks: LangChain/LangGraph 1.0 GA + migration guide · Anthropic "Building Effective Agents" / multi-agent token economics · OpenAI agents guide.
RAG: Anthropic contextual retrieval · voyage-context-4 · pgvector 0.8 release notes · ParadeDB hybrid-search manual · "When to Use Graphs in RAG" (arXiv:2506.05690) · agentic-RAG survey (arXiv:2501.09136).
Voice: OpenAI Realtime GA/pricing · LiveKit Agents docs/pricing + Expo SDK · Deepgram Flux · ElevenLabs Scribe v2/Agents pricing · Sarvam API pricing.
Mobile: Expo SDK 51–57 changelogs · RN 0.82–0.86 blog · Play Store API-36 + 16KB requirements · FlashList v2 · Reanimated 4 · NativeWind/Reusables/Uniwind docs · Vercel AI SDK Expo guide.
Compliance: DPDP Rules 2025 (Rule 10, §9(3), Fourth Schedule) · amended COPPA (Apr 2026) · EU AI Act Art 50 · Gemini API ToS (under-18 prohibition) · OpenAI under-18 API guidance · Anthropic minors guidelines · Character.AI/FTC 6(b) timeline.
Ops: Langfuse v3 platform / SDK v4 upgrade guides + MIT licensing · DeepEval/Ragas/promptfoo · LiteLLM docs.
Product: Khanmigo/Duolingo(+ABC, backlash)/Synthesis/Squirrel AI/MagicSchool/PW Alakh AI/SwiftChat/SigIQ · BYJU'S post-mortems · NCERT/NCF-SE rollout + CBSE 2026 exam pattern · UPI AutoPay/Razorpay edtech guides · WhatsApp parent-engagement case studies.

---

*End of plan. Feed phases sequentially to the coding agent; keep this document updated as the single source of truth for the refactor (supersedes `enhancement_plan.md`, `implementation_plan.md`, `phase2/3_implementation.md`, `ui_integration_plan.md` at repo root, and the pending-items table in the external `roadmap.md`).*
