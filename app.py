import os
from pathlib import Path
import json
import logging
import signal
import asyncio
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse, JSONResponse
import uvicorn

from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# project imports
from utils.util import init_logging
from utils.open_podcraft import OpenPodCraft

# global vars
open_pc = OpenPodCraft()
is_shutdown = False

# database configuration (SQLite)
DATABASE_URL = "sqlite:///./podcasts.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()
static_files = StaticFiles(
    directory=os.path.join(os.path.dirname(__file__), 'static'),
)
app.mount("/static", static_files, name='static')

# templates directory
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))

# SQLAlchemy model for a Podcast
class PodcastDB(Base):
    __tablename__ = "podcasts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    # Mark other fields as nullable so they can be empty initially
    description = Column(String, nullable=True)
    chapters = Column(String, nullable=True)
    transcript = Column(JSON, nullable=True)
    voice_names = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)

# Create the table(s)
Base.metadata.create_all(bind=engine)

# Pydantic model for request validation
class Podcast(BaseModel):
    title: str
    description: str
    chapters: str
    transcript: str
    voice_names: List[str]
    settings: Dict[str, Any]

class PodcastTitle(BaseModel):
    title: str
    
#### common api ####
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/voices", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("voices.html", {"request": request})

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# POST endpoint to create a new podcast entry
@app.post("/api/podcasts/create")
def create_podcast(podcast: PodcastTitle, db: Session = Depends(get_db)):
    # Use default values for other fields
    db_podcast = PodcastDB(
        title=podcast.title,
        description="",    # Default empty string
        chapters="",       # Default empty string
        transcript=[],     # Default empty list
        voice_names=[],    # Default empty list
        settings={}        # Default empty dict
    )
    db.add(db_podcast)
    db.commit()
    db.refresh(db_podcast)
    return {"message": "Podcast created", "id": db_podcast.id}

# POST endpoint to create a new podcast entry
# @app.post("/api/podcasts/create")
# def create_podcast(podcast: Podcast, db: Session = Depends(get_db)):
#     db_podcast = PodcastDB(
#         title=podcast.title,
#         description=podcast.description,
#         chapters=podcast.chapters,
#         transcript=podcast.transcript,
#         voice_names=podcast.voice_names,
#         settings=podcast.settings,
#     )
#     db.add(db_podcast)
#     db.commit()
#     db.refresh(db_podcast)
#     return {"message": "Podcast created", "id": db_podcast.id}

# Optional: GET endpoint to list all podcasts (for testing)
@app.get("/api/podcasts/get")
def read_podcasts(db: Session = Depends(get_db)):
    podcasts = db.query(PodcastDB).all()
    return podcasts

@app.get("/podcasts/{podcast_id}")
def read_podcast(request: Request, podcast_id: str, db: Session = Depends(get_db)):
    global open_pc
    podcast = db.query(PodcastDB).filter(PodcastDB.id == podcast_id).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    open_pc.curr_podcast_uuid = podcast.id
    open_pc.chapters = podcast.chapters
    open_pc.set_podcast_script_from_dict(podcast.transcript)
    podcasts_audio_file_path = os.path.join("static", "audio_outputs", "podcast-" + str(open_pc.curr_podcast_uuid), "final.wav")
    if os.path.exists(podcasts_audio_file_path):
        open_pc.flags["is_podcast_available"] = True
    return templates.TemplateResponse("podcasts.html", {"request": request, "podcast": podcast})

@app.post("/api/generate_podcast_script")
async def generate_podcast_script(
        podcast_uuid: str = Form(...), 
        title: str = Form(...), 
        description: str = Form(...), 
        content: str = Form(...), 
        extra_prompt: str = Form(...), 
        llmModel: str = Form(...), 
        num_speakers: str = Form(...), 
        podcast_len: str = Form(...), 
        db: Session = Depends(get_db)
    ):
    global open_pc

    podcast = db.query(PodcastDB).filter(PodcastDB.id == podcast_uuid).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

     # Update the podcast fields with the new data
    podcast.title = title.strip()
    podcast.description = description.strip()
    podcast.chapters = content.strip()
    podcast.settings = {
        "extra_prompt": extra_prompt,
        "llmModel": llmModel,
        "num_speakers": num_speakers,
        "podcast_len": podcast_len
    }

    # Save the updates to the database.
    db.commit()
    db.refresh(podcast)

    if open_pc is None:
        print("Open PC not initialized!!!")
        return

    open_pc.chapters = content
    open_pc.run_in_thread("generate_podcast_script")

    return {"message": "Podcast updated successfully", "podcast_id": podcast.id}   

@app.post("/api/generate_podcast")
async def generate_podcast_script(
        podcast_uuid: str = Body(..., media_type="text/plain"),
        db: Session = Depends(get_db)
    ):
    global open_pc

    podcast = db.query(PodcastDB).filter(PodcastDB.id == podcast_uuid).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    if open_pc is None:
        print("Open PC not initialized!!!")
        return

    open_pc.run_in_thread("generate_podcast")
    return {"message": "Podcast updated successfully", "podcast_id": podcast.id}    

@app.post("/api/podcasts/save-transcript")
async def save_transcript(
        podcast_uuid: str = Body(..., media_type="text/plain"),
        db: Session = Depends(get_db)
    ):
    global open_pc

    # Retrieve the podcast from the database using the provided UUID
    podcast = db.query(PodcastDB).filter(PodcastDB.id == podcast_uuid).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    if open_pc is None:
        logging.warning("Open PC not initialized!!!")
        return
        
    podcast.transcript = open_pc.get_podcast_script_as_dict()
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating transcript: {e}")
    
    db.refresh(podcast)
    return {"message": "Transcript updated successfully", "podcast_id": podcast.id}

@app.get("/api/get_podcast_audio_url")
async def get_audio_url():
    global open_pc
    audio_url = os.path.join("static", "audio_outputs", "podcast-"+str(open_pc.curr_podcast_uuid), "final.wav")  
    audio_url = os.sep+audio_url  
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    return JSONResponse(content={"audio_url": audio_url})

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