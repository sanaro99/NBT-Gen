"""FastAPI app for NBT-Gen.

Routes:
- GET  /                — the form
- POST /generate        — no-JS fallback: runs the pipeline once, server-renders
- GET  /generate-stream — SSE: streams status, then the final result in-stream
                          (the browser renders that result directly — it never
                          re-submits, so the pipeline runs exactly once)
"""
import asyncio
import json
import os

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config
from .pipeline import generate_idea

log = config.log.getChild("web")

app = FastAPI(title="Never-Before-Thought Generator", version=config.VERSION)

_BASE = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(_BASE, "../static")), name="static")
templates = Jinja2Templates(directory=os.path.join(_BASE, "../templates"))


def _clean_topic(topic: str) -> str:
    topic = (topic or "").strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Topic must not be empty.")
    if len(topic) > config.MAX_TOPIC_LEN:
        raise HTTPException(status_code=422,
                            detail=f"Topic too long (max {config.MAX_TOPIC_LEN} characters).")
    return topic


def _clamp_wildness(wildness) -> int:
    try:
        return max(0, min(int(wildness), 100))
    except (TypeError, ValueError):
        return 50


@app.get("/")
def read_index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"idea": None})


@app.post("/generate")
def generate(request: Request, topic: str = Form(...), wildness: int = Form(50)):
    topic = _clean_topic(topic)
    wildness = _clamp_wildness(wildness)
    try:
        data = generate_idea(topic, wildness=wildness)
    except Exception as exc:
        log.exception("generation failed")
        raise HTTPException(status_code=500, detail=str(exc))
    return templates.TemplateResponse(request, "index.html", {
        "topic": topic, "wildness": wildness, **data,
    })


@app.get("/generate-stream")
async def generate_stream(topic: str, wildness: int = 50):
    """Server-Sent Events: status updates followed by the final result."""
    topic = _clean_topic(topic)
    wildness = _clamp_wildness(wildness)

    async def event_generator():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def status_callback(message: str):
            # Called from the worker thread — hop back onto the event loop safely.
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "status", "message": message}
            )

        async def run():
            try:
                result = await asyncio.to_thread(
                    generate_idea, topic, wildness, status_callback
                )
                await queue.put({"type": "result", "data": result})
            except Exception as exc:
                log.exception("streamed generation failed")
                await queue.put({"type": "error", "message": str(exc)})
            finally:
                await queue.put(None)  # sentinel

        task = asyncio.create_task(run())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")
