# CLAUDE.md

Guidance for working in this repo.

## What this is

**NBT-Gen = "Never-Before-Thought Generator"** — a FastAPI web app that turns a
*topic* + a *wildness* slider (0–100) into one short speculative paragraph that aims
to be **novel**, **coherent**, and **surprising**. It is **not** a Minecraft NBT
tool. The product is the *idea*; everything else serves making that idea good.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env          # then fill in GEMINI_API_KEY and MISTRAL_API_KEY
uvicorn app.main:app --reload # http://localhost:8000
pytest                        # all API calls are mocked — no keys/network needed
```

Requires `GEMINI_API_KEY` (creative stages) and `MISTRAL_API_KEY` (judge). All
tunables live in `app/config.py` and are overridable via env (see `.env.example`).

## Pipeline (best-of-N) — `app/pipeline.py:generate_idea`

```
mine ONCE → compose N candidates (parallel) → judge ALL in one call → polish winner
```

1. **`modules/miner.py`** (Gemini, structured JSON) — ~12 tagged assumptions, mined
   once per request.
2. **`modules/composer.py`** (Gemini, `N_CANDIDATES` in parallel) — each candidate
   twists a *different* assumption with a *different* **divergence operator**
   (`invert`/`merge`/`rescale`/`reverse_causality`/`substrate_swap`). Temperature is
   `wildness_to_temperature()` (0.6–1.3, capped — never the 2.0 that makes Gemini
   incoherent).
3. **`modules/judge.py`** (Mistral, one comparative call) — scores every candidate on
   coherence/novelty/surprise and ranks them. Returns
   `{"ranked": [...], "scoring_degraded": bool}`.
4. **`modules/safety.py`** (Gemini) — polishes only the winner.

Model split is intentional: **Gemini creates, Mistral judges** (an independent judge
reduces self-grading bias).

## Routes — `app/main.py`

| route | purpose |
|-------|---------|
| `GET /` | the form |
| `POST /generate` | **fallback only** (no-JS): one run, server-rendered |
| `GET /generate-stream` | SSE: streams `status` events, then a final `result` event |

The browser uses the SSE endpoint and renders the `result` **in place**.

## Non-obvious things / gotchas

- **Never re-submit to render a result.** The original bug: the SSE `result` was
  discarded and the form re-POSTed, running the pipeline twice and showing a
  *different* idea than the one streamed. The frontend (`templates/index.html`,
  `renderResult`) now paints the streamed `result` directly. Keep it that way.
- **Free-tier Gemini = 5 requests/minute.** One generation ≈ `1 + N_CANDIDATES + 1`
  Gemini calls, so `N_CANDIDATES` defaults to **3** to fit. Raising it improves
  quality but costs quota. The pipeline degrades gracefully: failed composer
  candidates are skipped, and a failed polish call falls back to the unpolished
  winner (`pipeline.py`). Transient 5xx are retried in `config.gemini_generate`;
  429 is not (the wait is too long to be useful live).
- **No silent scoring.** If the Mistral judge is unreachable, `judge.py` uses a
  local heuristic and sets `scoring_degraded=True` (surfaced in the UI) — it never
  quietly passes a fake 0.5 novelty.
- **All Gemini calls go through `config.gemini_generate(...)`**, not the client
  directly — that's where retry/backoff lives.
- **Mistral is called via `requests`** against the REST API (structured
  `response_format` JSON), *not* the `mistralai` SDK — the SDK's lazy-import package
  doesn't resolve on Python 3.14. Don't reintroduce the SDK without checking the
  local interpreter.
- **Starlette 1.x signature:** `templates.TemplateResponse(request, name, context)`
  (request first). The legacy `(name, {"request": ...})` form is gone.

## Tests — `tests/` (pytest, fully mocked)

`tests/conftest.py` sets dummy keys so imports don't need a real `.env`. Tests stub
the stage functions / API calls, so they're fast and offline. When you change the
pipeline contract, update `test_pipeline.py` (it asserts mine-once + one judge call +
graceful fallbacks).
