# Never-Before-Thought Generator (NBT-Gen)

_A web application that outputs weird-yet-meaningful "never-before-thought" ideas._  
Built with **FastAPI**, **Jinja2 Templates** (Bootstrap 5 & [NES.css](https://github.com/nostalgic-css/NES.css)), and **Gemini** (1.5, 2.0, 2.5 Flash Preview) AI models.

---

## 1  Project purpose
To build an autonomous creativity pipeline that takes any **topic** (e.g. *“plate tectonics”*) and returns a short, speculative thought that is:
* **Novel** – unlikely to exist in public discourse or AI training data.
* **Coherent** – grammatically correct and internally logical.
* **Surprising** – inverts or twists a core assumption of the topic.

---

## 2  System architecture (high-level)
```
┌────────────┐    ┌──────────────┐    ┌────────────────────┐    ┌─────────────┐
│  FastAPI   │─>──│ Assumption   │─>──│   Divergent Idea   │─>──│ Plausibility│
│  endpoint  │    │  Miner       │    │     Composer       │    │   Filter    │
│  /generate │    │ (Gemini 1.5) │    │(Gemini 2.5, T(0-2))│    │             │
└────────────┘    └──────────────┘    └────────────────────┘    └─────────────┘
                                                                       │
                                        ┌──────────────────────────────┴────────────┐
                                        │ Novelty Scorer (embedding distance + web) │
                                        └──────────────────────────────┬────────────┘
                                                                       │
                                                          ┌────────────┴───────────┐
                                                          │ Safety & Final Polish  │
                                                          │     (Gemini 2.0)       │
                                                          └────────────┬───────────┘
                                                                       │
                                          Server-rendered Web UI via Jinja2 Templates
```
1. **Assumption Miner** – calls Gemini 1.5 with `temperature≈0` to generate a list of canonical premises of the user topic.  
2. **Assumption Tweaker + Idea Composer** – single Gemini 2.5 Flash Preview call at temperature defined by wildness slider by the user; flips one premise and expands it into a < 80-word paragraph.
3. **Plausibility Filter** – rejects gibberish via perplexity + grammar check.
4. **Novelty Scorer** – To be implemented.
   * cosine distance to nearest sentence in an embedded Wikipedia subset (FAISS).
   * web hit-count via Bing search API.
5. **Safety Guard & Polish** – Gemini 2.0 rewriter with system prompt _“Rewrite clearly, remove disallowed content.”_
6. **Frontend** – Server-rendered Jinja2 templates using Bootstrap 5 & NES.css for UI.

---

## 3  API design
| verb | path        | data                         | description                              |
|------|-------------|------------------------------|------------------------------------------|
| POST | `/generate` | Form data: `topic` (string), `wildness` (0-100) | Renders page with generated idea and preserves input |

---

## 4  quick-start (local)
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

### required environment variables
| name | purpose |
|------|---------|
| `GEMINI_API_KEY` | Google AI Studio key for Gemini models |

---

## 5  project layout
```
NBT-Gen/
├─ app/                  # FastAPI modules
├─ templates/            # Jinja2 HTML templates
├─ static/               # CSS & static assets
├─ requirements.txt
├─ .env.example
└─ README.md
```

---

## 6  extending
* **Embed feedback loop** – thumbs-up/down to inform future fine-tuning.
* **Add local fallback** – Mistral/phi-2 for offline or quota-safe operation.

---

## 7  license
GNU v3 for source code. Gemini usage governed by Google AI Studio terms.