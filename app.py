import os
from pathlib import Path
import json
import logging
import signal
import asyncio
import uuid
from typing import List, Dict

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse, JSONResponse
import uvicorn

# project imports
from utils.util import init_logging
from utils.open_podcraft import OpenPodCraft

# global vars
open_pc = OpenPodCraft()
is_shutdown = False

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

@app.get("/voices", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("voices.html", {"request": request})


@app.post("/api/generate_podcast_script")
async def generate_podcast_script(
        title: str = Form(...), 
        content: str = Form(...), 
    ):
    global open_pc

    if open_pc is None:
        print("Open PC not initialized!!!")
        return

    open_pc.chapters = content
    open_pc.run_in_thread("generate_podcast_script")

@app.get("/api/get_podcast_script")
async def get_podcast_script():
    global open_pc

    if open_pc is None:
        return {"status": "not found"}
    
    return open_pc.get_podcast_script_as_dict()

@app.get("/api/check_flags")
async def check_flags():

    async def fetch_flags_state(sleep_time_s: float = 0.1):
        global is_shutdown, open_pc

        prev_flag_state = None
        while not is_shutdown:

            if open_pc is None:
                await asyncio.sleep(sleep_time_s)
                continue
            
            if prev_flag_state is None or open_pc.flags != prev_flag_state:
                prev_flag_state = open_pc.flags.copy()
                yield f"data: {json.dumps(open_pc.flags)}\n\n"

            await asyncio.sleep(sleep_time_s)

    return StreamingResponse(fetch_flags_state(), media_type="text/event-stream")

def get_wav_files(directory: Path) -> List[Dict[str, str]]:
    """
    Retrieve all .wav files from the specified directory.

    Args:
        directory (Path): The directory path to search for .wav files.

    Returns:
        List[Dict[str, str]]: A list of dictionaries where each dictionary contains:
            - "filename": the base name of the file (without extension)
            - "filepath": the full path to the file as a string.
    """
    if not directory.exists() or not directory.is_dir():
        return []

    return [
        {
            "filename": file.stem,
            "filepath": str(file)
        }
        for file in directory.iterdir()
        if file.is_file() and file.suffix.lower() == ".wav"
    ]


@app.get("/api/voices/get-info")
async def get_voices() -> Dict[str, List[Dict[str, str]]]:
    """
    Get information on .wav files from both the 'static/voices' and 'static/voices/custom' directories.

    Returns:
        Dict[str, List[Dict[str, str]]]: A JSON object with two keys:
            - "voices": List of .wav files from 'static/voices'
            - "custom_voices": List of .wav files from 'static/voices/custom'
    """
    voices_dir = Path("static") / "voices"
    custom_voices_dir = voices_dir / "custom"

    voices = get_wav_files(voices_dir)
    custom_voices = get_wav_files(custom_voices_dir)

    return {"voices": voices, "custom_voices": custom_voices}

@app.post("/api/voices/upload")
async def upload_voice(
    file: UploadFile = File(...),
    voiceName: str = Form(...)
) -> JSONResponse:
    """
    Upload an audio file with an associated voice name and store it as a .wav file in the 
    'static/voices/custom' directory. If a file with the same voice name exists, a counter is 
    appended to the filename to ensure uniqueness.

    Args:
        file (UploadFile): The audio file uploaded.
        voiceName (str): The name of the voice provided in the form data.

    Returns:
        JSONResponse: A JSON object containing the unique filename under the key "filename".
    """
    voices_dir = Path("static") / "voices" / "custom"
    voices_dir.mkdir(parents=True, exist_ok=True)

    # Clean and format the voice name
    base_name = voiceName.strip().replace(" ", "_")
    if not base_name:
        base_name = str(uuid.uuid4())

    # Ensure file extension is .wav
    ext = Path(file.filename).suffix.lower()
    if ext != ".wav":
        ext = ".wav"

    # Build the filename and check for duplicates
    filename = f"{base_name}{ext}"
    file_location = voices_dir / filename
    counter = 1
    while file_location.exists():
        filename = f"{base_name}_{counter}{ext}"
        file_location = voices_dir / filename
        counter += 1

    try:
        content = await file.read()
        file_location.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return JSONResponse({"filename": filename})

def handle_interrupt(signum, frame):
    global is_shutdown, open_pc

    logging.info("Interrupt received, terminating app !!")
    is_shutdown = True
    open_pc.stop_all_threads()

def run_web_app():
    global open_pc

    init_logging()
    # open_pc = OpenPodCraft()

    signal.signal(signal.SIGINT, handle_interrupt)
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=2)

if __name__ == "__main__":   
    run_web_app()