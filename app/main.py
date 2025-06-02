import os
import random
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from .pipeline import generate_idea

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
