import os
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
import uvicorn

app = FastAPI()
static_files = StaticFiles(
    directory=os.path.join(os.path.dirname(__file__), 'static'),
)
app.mount("/static", static_files, name='static')

# templates directory
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))


#### common api ####
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/generate_podcast_script")
async def generate_podcast_script(
        title: str = Form(...), 
        content: str = Form(...), 
    ):

    print(title)
    print(content)

def run_web_app():
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=2)

if __name__ == "__main__":   
    run_web_app()