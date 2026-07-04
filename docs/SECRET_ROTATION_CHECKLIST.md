# 🔐 Secret Rotation Checklist (URGENT — deferred)

> The repo `rspventures/ai_ed_tech` was **public** with these secrets committed in plaintext. Assume all are compromised (automated scrapers harvest public-repo keys within minutes). History has been purged + force-pushed and the repo should be set private, but **that does not un-leak already-scraped keys.** Rotate every item below.
>
> Local backup of the old `.env` and `ai-tutor-key.pem`: `…/scratchpad/secrets_backup/` (this session's scratchpad). Use it only to know *which* values to revoke.

## Providers — revoke old key, issue new, update `.env` (local) + deployment env

| # | Secret (`.env` key) | Where to rotate | Notes |
|---|---|---|---|
| 1 | `OPENAI_API_KEY` | platform.openai.com → API keys → revoke + create | Check usage dashboard for abuse spikes first |
| 2 | `COHERE_API_KEY` | dashboard.cohere.com → API keys | Used for RAG rerank |
| 3 | `SARVAM_API_KEY` | dashboard.sarvam.ai | Being removed in Phase 2, but revoke now |
| 4 | `ELEVENLABS_API_KEY` | elevenlabs.io → Profile → API keys | Voice STT/TTS |
| 5 | `SECRET_KEY` (JWT) | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` | Rotating **invalidates all existing JWTs/sessions** — users re-login (acceptable) |
| 6 | `NEO4J_PASSWORD` | Neo4j being deleted in Phase 2; change container pw meanwhile | docker-compose `NEO4J_AUTH` |
| 7 | DB / Redis creds (`DATABASE_URL`, `REDIS_URL`) | If they contain non-default passwords, rotate at the DB/Redis level | Compose uses `postgres/postgres` locally — set real creds for any deployed instance |
| 8 | `LANGFUSE_*` keys | Langfuse UI → Settings → API keys (self-hosted) | Also rotate `SALT`/`ENCRYPTION_KEY`/`NEXTAUTH_SECRET` in compose (currently placeholders) |

## AWS SSH key pair — `ai-tutor-key.pem` (private key was committed!)

9. **Delete the key pair in EC2** (EC2 → Network & Security → Key Pairs) and create a new one.
10. For any running instance that used it: create a new key pair, add the new **public** key to the instance's `~/.ssh/authorized_keys` (via SSM Session Manager or console), then remove the old one. Rotate the pem locally; never commit it.
11. Audit that instance's CloudTrail / auth logs for unauthorized SSH while the key was public.

## After rotation

- [ ] Update local `.env` (already gitignored — verify with `git check-ignore .env` → should print `.env`).
- [ ] Update the deployment's environment (compose `.env`, CI secrets, EC2 env) — **not** by committing.
- [ ] Enable **GitHub secret scanning + push protection** (Settings → Code security) so this can't recur.
- [ ] Confirm repo visibility = **Private**.
- [ ] Optionally notify anyone who had repo access that history was rewritten (they must `git fetch --all && git reset --hard origin/<branch>` or re-clone; a stale clone can re-introduce the secrets).

## Why this can't wait

A leaked `OPENAI_API_KEY` on a public repo is the classic vector for surprise five-figure bills from crypto-mining prompt abuse. Items 1–4 (paid API keys) and 9–11 (SSH into your server) are the highest urgency.
