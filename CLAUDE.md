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

## Pipeline (lean best-of-N) — `app/pipeline.py:generate_idea`

```
generate N candidates (ONE structured Gemini call) → judge ALL (one Mistral call) → best
        ↑ if best is below the bar and scoring is reliable, run one more round
```

1. **`modules/generator.py`** (Gemini, one structured-JSON call) — mines the topic's
   assumptions *internally* and emits `N_CANDIDATES` finished candidate ideas, each
   tagged with the `assumption` it twists and the `operator` used
   (`invert`/`merge`/`rescale`/`reverse_causality`/`substrate_swap`). Prose comes back
   already clean (polish rules are folded into the prompt — there is no separate polish
   stage). Temperature is `wildness_to_temperature()` (0.6–1.3, capped — never the 2.0
   that makes Gemini incoherent).
2. **`modules/judge.py`** (Mistral, one comparative call) — scores every candidate on
   coherence/novelty/surprise and ranks them. Returns
   `{"ranked": [...], "scoring_degraded": bool}`.

So a generation is **~1 Gemini call per round** (not ~5). Model split is intentional:
**Gemini generates, Mistral judges** (an independent judge reduces self-grading bias).
History: an earlier version had separate `miner.py` / `composer.py` (parallel
per-candidate) / `safety.py` (polish) — collapsed into `generator.py` to cut API
calls and latency.

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
- **Free-tier Gemini quota is brutal and PER-MODEL PER-DAY.** Measured on this
  project: `gemini-2.5-flash` = **20 requests/day**; `gemini-2.0-flash` = **0** (not
  available). The lean pipeline uses ~1 Gemini call/generation (one structured call
  produces all `N_CANDIDATES`), so the free tier allows ~20 generations/day instead
  of ~4. `N_CANDIDATES` (default 5) no longer multiplies the call count — only output
  tokens. Transient 5xx are retried in `config.gemini_generate`; 429 is not (the wait
  is too long to be useful live). Daily quota resets ~midnight Pacific; a paid key
  removes the limit.
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
pipeline contract, update `test_pipeline.py` (it asserts one generate call + one
judge call per round, second round only when the best is below the bar, and
short-circuit when scoring is degraded).
