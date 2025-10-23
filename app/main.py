import os
import random
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from .pipeline import generate_idea
import asyncio
import json
from queue import Queue
from threading import Thread

app = FastAPI(title="Never-Before-Thought Generator", version="0.1.0")

# mount static assets (css, images, etc.)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../static")), name="static")

# configure Jinja2 templates directory
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

@app.get("/")
def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "idea": None, "novelty": None})

@app.post("/generate")
def generate(request: Request, topic: str = Form(...), wildness: int = Form(50)):
    try:
        # generate one idea using slider-controlled wildness
        data = generate_idea(topic, wildness=wildness)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "idea": data["idea"],
            "novelty": data["novelty"],
            "topic": topic,
            "wildness": wildness,
            "coherence": data["coherence"],
            "version": data["version"]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generate-stream")
async def generate_stream(topic: str, wildness: int = 50):
    """Server-Sent Events endpoint for real-time status updates"""
    async def event_generator():
        status_queue = Queue()
        result_container = {}
        
        def status_callback(status: str):
            status_queue.put({"type": "status", "message": status})
        
        def run_generation():
            try:
                result = generate_idea(topic, wildness=wildness, status_callback=status_callback)
                result_container["data"] = result
                status_queue.put({"type": "result", "data": result})
            except Exception as e:
                status_queue.put({"type": "error", "message": str(e)})
            finally:
                status_queue.put(None)  # Signal completion
        
        # Run generation in background thread
        thread = Thread(target=run_generation)
        thread.start()
        
        while True:
            # Check queue with timeout to avoid blocking
            await asyncio.sleep(0.1)
            
            if not status_queue.empty():
                status = status_queue.get()
                
                if status is None:
                    break
                
                yield f"data: {json.dumps(status)}\n\n"
        
        thread.join()
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
