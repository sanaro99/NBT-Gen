# Never-Before-Thought Generator (NBT-Gen)

_A web application that outputs weird-yet-meaningful "never-before-thought" ideas._  
Built with a **FastAPI** backend, **Jinja2 Templates** (Bootstrap 5 & [NES.css](https://github.com/nostalgic-css/NES.css)) for UI, **Gemini 2.5 Flash** for assumption mining, idea composition, and final polish, and **Mistral-small** as an independent **comparative judge** for coherence, novelty & surprise.

It uses a **best-of-N** strategy: for each topic it composes several divergent ideas in parallel and a single judge call ranks them, so the idea you get is the strongest of the batch — not one lucky random draw.

---

## 1  Project Purpose
To build an autonomous creativity pipeline that takes any **topic** (e.g. *"plate tectonics"*) and returns a short, speculative thought that is:
* **Novel** – unlikely to exist in public discourse or AI training data.
* **Coherent** – grammatically correct and internally logical.
* **Surprising** – inverts or twists a core assumption of the topic.

---

## 2  System Architecture (high-level)
```
topic + wildness
      │
      ▼  Gemini  (mine ONCE, structured JSON)
[1] Assumption Miner ──► ~12 assumptions (textbook facts + hidden axioms)
      │
      ▼  Gemini ×N in parallel (capped temp, varied divergence operators)
[2] Divergent Composer ──► N candidate paragraphs {assumption, operator}
      │
      ▼  Mistral-small  (ONE comparative call, structured JSON)
[3] Comparative Judge ──► per-candidate coherence / novelty / surprise + ranking
      │                     keep the best; if below the bar → one more round
      ▼  Gemini  (light edit, preserve the creative soul)
[4] Safety & Final Polish ──► final idea
      │
      ▼  SSE → server-rendered Jinja2 UI
```
1. **Assumption Miner** – Gemini at `temperature≈0.3` extracts ~12 premises (textbook facts + subtle hidden axioms) via structured JSON, **once** per request.
2. **Divergent Composer** – Gemini composes `N_CANDIDATES` (default 3) paragraphs **concurrently**, each applying a different **divergence operator** (`invert`, `merge`, `rescale`, `reverse_causality`, `substrate_swap`) to a different assumption. The wildness slider sets a capped sampling temperature (0.6–1.3) and the conceptual reach of the twist.
3. **Comparative Judge** – Mistral-small scores **all** candidates in one call on coherence, novelty and surprise [0–1] and ranks them. If the judge API is unavailable it degrades to a transparent local heuristic (surfaced as `scoring_degraded`, never a silent pass).
4. **Safety & Final Polish** – Gemini polishes the single winning candidate for clarity while preserving the creative soul.
5. **Frontend** – Server-rendered Jinja2 templates (Bootstrap 5, NES.css, dark/light toggle, wildness slider). Status streams over SSE and the final result renders **in place** — the pipeline runs exactly once.

---

## 3  API Design
| verb | path               | data                                            | description                                                        |
|------|--------------------|-------------------------------------------------|--------------------------------------------------------------------|
| GET  | `/`                | –                                               | Renders the form                                                   |
| POST | `/generate`        | Form: `topic` (string), `wildness` (0-100)      | No-JS fallback: runs the pipeline once, server-renders the result  |
| GET  | `/generate-stream` | Query: `topic`, `wildness`                      | SSE: streams `status` events then a final `result` event           |

The browser uses `/generate-stream` and renders the `result` event **in place**; `POST /generate` is the progressive-enhancement fallback when JavaScript/SSE is unavailable.

### Result / Template Context
| key               | type    | description                                            |
|-------------------|---------|--------------------------------------------------------|
| topic             | string  | The input topic                                        |
| wildness          | integer | Wildness slider value (0–100)                          |
| idea              | string  | Final polished speculative idea                        |
| coherence         | float   | Coherence score [0–1] (judge)                          |
| novelty           | float   | Novelty score [0–1] (judge)                            |
| surprise          | float   | Surprise score [0–1] (judge)                           |
| assumption        | string  | The assumption that was twisted                        |
| operator          | string  | Divergence move applied (e.g. `invert`, `rescale`)     |
| scoring_degraded  | bool    | `true` if scores came from the local fallback heuristic|
| version           | string  | Pipeline version identifier                            |

---

## 4  Quick-start (local)
```bash
# clone repo
$ git clone https://github.com/sanaro99/NBT-Gen.git && cd NBT-Gen

# create .env
$ cp .env.example .env

# install dependencies
$ pip install -r requirements.txt

# run server
$ uvicorn app.main:app --reload
```

### Environment Variables
| name                    | purpose                                                        |
|-------------------------|----------------------------------------------------------------|
| `GEMINI_API_KEY`        | **Required.** Google AI Studio key (miner, composer, polish)   |
| `MISTRAL_API_KEY`       | **Required.** Mistral key for the comparative judge            |
| `GEMINI_MODEL`          | Miner & polish model (default `models/gemini-2.5-flash`)       |
| `GEMINI_COMPOSER_MODEL` | Composer model (default = `GEMINI_MODEL`)                      |
| `MISTRAL_MODEL`         | Judge model (default `mistral-small-latest`)                   |
| `NBT_N_CANDIDATES`      | Best-of-N candidates per round (default `3`; higher = better & costlier) |
| `NBT_MAX_ROUNDS`        | Compose+judge rounds before returning best (default `2`)       |
| `NBT_MIN_COHERENCE` / `NBT_MIN_NOVELTY` | Quality bar (defaults `0.5` / `0.55`)          |

See `.env.example` for the full list of tunables.

---

## 5  Project Layout
```
NBT-Gen/
├─ app/
│  ├─ main.py            # FastAPI routes (/, /generate, /generate-stream)
│  ├─ config.py          # env reads, tunables, shared Gemini client
│  ├─ pipeline.py        # best-of-N orchestration
│  └─ modules/
│     ├─ miner.py        # [1] assumptions  (Gemini, structured JSON)
│     ├─ composer.py     # [2] best-of-N candidates (Gemini, parallel)
│     ├─ judge.py        # [3] comparative scoring (Mistral)
│     └─ safety.py       # [4] final polish (Gemini)
├─ templates/index.html  # UI + SSE client
├─ static/               # screenshots & static assets
├─ tests/                # pytest suite (API calls mocked)
├─ requirements.txt
├─ .env.example
├─ Dockerfile
└─ README.md
```

---

## 6  Extending
* **Web-grounded novelty** – ground the novelty score in a real prior-art/search signal instead of the model's judgment alone.
* **Feedback loop** – thumbs-up/down to inform future tuning.
* **Tune the search** – raise `NBT_N_CANDIDATES` / `NBT_MAX_ROUNDS` for higher quality at more cost.

---
## 7  Sample Outputs
#### Sample output for topic: 'plate tectonics'

##### with wildness as 0
![Plate tectonics with wildness 0](static/screenshots/nbt-plate-tectonics-0.png "Sample output for topic: 'plate tectonics' with wildness 0")

##### with wildness as 100
![Plate tectonics with wildness 100](static/screenshots/nbt-plate-tectonics-100.png "Sample output for topic: 'plate tectonics' with wildness 100")

#### Sample output for topic: 'observable universe'
![Output for topic: 'observable universe'](static/screenshots/nbt-1.png "Sample output for topic: 'observable universe'")

#### Sample output for topic: 'jupiter is a gas giant'
![Output for topic: 'jupiter is a gas giant'](static/screenshots/nbt-2.png "Sample output for topic: 'jupiter is a gas giant'")

#### Sample output for topic: 'photosynthesis' on a small screen device
![Output for topic: 'photosynthesis'](static/screenshots/nbt-3.png "Sample output for topic: 'photosynthesis'")

## 8  License
GNU v3 for source code. Gemini usage governed by Google AI Studio terms.