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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# project imports
from utils.util import init_logging, get_wav_files, setup_logging
from utils.open_podcraft import OpenPodCraft
from database import Base, PodcastDB
from io import BytesIO
from pydub import AudioSegment

setup_logging()

# global vars
open_pc = OpenPodCraft()
is_shutdown = False

# database configuration (SQLite)
DATABASE_URL = "sqlite:///./podcasts.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine) # create the table(s)

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
    global open_pc

    if open_pc is None:
        logging.warning("Open PodCraft not initialized!!!")
        return {"status": "fail"}    
    open_pc.reset()

    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/voices", response_class=HTMLResponse)
async def index_page(request: Request):
    global open_pc

    if open_pc is None:
        logging.warning("Open PodCraft not initialized!!!")
        return {"status": "fail"}    
    open_pc.reset()

    return templates.TemplateResponse("voices.html", {"request": request})

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

#### podcast api ####
class PodcastTitle(BaseModel):
    title: str

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
    if os.path.exists(podcasts_audio_file_path): open_pc.flags["is_podcast_available"] = True
        
    return templates.TemplateResponse("podcasts.html", {"request": request, "podcast": podcast})
    
@app.post("/api/podcasts/create")
def create_podcast(podcast: PodcastTitle, db: Session = Depends(get_db)):

    db_podcast = PodcastDB(
        title=podcast.title,
        description="",
        chapters="",
        transcript=[],
        voice_names=[],
        settings={}
    )
    db.add(db_podcast)
    db.commit()
    db.refresh(db_podcast)
    return {"message": "Podcast created", "id": db_podcast.id}

@app.get("/api/podcasts/get")
def read_podcasts(db: Session = Depends(get_db)):
    podcasts = db.query(PodcastDB).all()
    return podcasts

@app.post("/api/podcasts/generate-script")
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

    if content == "" or title == "":
        logging.warning("You must provide content and title to generate script!!")
        return {"status": "fail"}   

    if open_pc is None:
        logging.warning("Open PodCraft not initialized!!!")
        return {"status": "fail"}    
    
    if open_pc.flags["is_generating_script"]:
        logging.warning("Script generation already in progress !!")
        return {"status": "fail"}   

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

    open_pc.chapters = content
    open_pc.llm_model_type = llmModel
    open_pc.user_prompt = extra_prompt
    open_pc.num_speakers = num_speakers
    open_pc.podcast_len = podcast_len.split(" ")[0]
    open_pc.run_in_thread("generate_podcast_script")

    return {"status": "success"}   

@app.post("/api/podcasts/generate-podcast")
async def generate_podcast_script(
        podcast_uuid: str = Body(..., media_type="text/plain"),
        db: Session = Depends(get_db)
    ):
    global open_pc

    if open_pc is None:
        logging.info("Open PodCraft not initialized!!!")
        return {"status": "fail"}  

    podcast = db.query(PodcastDB).filter(PodcastDB.id == podcast_uuid).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")     

    open_pc.run_in_thread("generate_podcast")
    return {"status": "success"}    

@app.get("/api/podcasts/get-audio-url")
async def get_audio_url():
    global open_pc
    audio_url = os.path.join("static", "audio_outputs", "podcast-"+str(open_pc.curr_podcast_uuid), "final.wav")  
    audio_url = os.sep+audio_url  
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    return JSONResponse(content={"audio_url": audio_url})

@app.get("/api/podcasts/get-script")
async def get_podcast_script(db: Session = Depends(get_db)):
    global open_pc

    if open_pc is None or open_pc.curr_podcast_uuid is None:
        return {"status": "not found"}
    
    podcast = db.query(PodcastDB).filter(PodcastDB.id == open_pc.curr_podcast_uuid).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")      
    
    
    podcast.transcript = open_pc.get_podcast_script_as_dict()
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating transcript: {e}")
    
    db.refresh(podcast)    
    return open_pc.get_podcast_script_as_dict()

#### voices api ####
@app.get("/api/voices/get-info")
async def get_voices_info() -> Dict[str, List[Dict[str, str]]]:
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
async def upload_voice(file: UploadFile = File(...), voiceName: str = Form(...)) -> JSONResponse:
    """
    Upload an audio file, convert it to a WAV file, and store it in the 
    'static/voices/custom' directory. If a file with the same voice name exists,
    a counter is appended to the filename to ensure uniqueness.
    """
    voices_dir = Path("static") / "voices" / "custom"
    voices_dir.mkdir(parents=True, exist_ok=True)

    # Clean and format the voice name
    base_name = voiceName.strip().replace(" ", "_")
    if not base_name:
        base_name = str(uuid.uuid4())

    # Prepare a unique filename with .wav extension
    filename = f"{base_name}.wav"
    file_location = voices_dir / filename
    counter = 1
    while file_location.exists():
        filename = f"{base_name}_{counter}.wav"
        file_location = voices_dir / filename
        counter += 1

    try:
        # Read file content from the uploaded file
        content = await file.read()
        audio_bytes = BytesIO(content)

        # Convert the audio file to WAV regardless of original format.
        # pydub will attempt to infer the format automatically.
        try:
            audio = AudioSegment.from_file(audio_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unsupported or invalid audio format: {e}")

        # Export the audio in WAV format to the designated file location.
        audio.export(file_location, format="wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return JSONResponse({"filename": filename})

class VoiceUpdate(BaseModel):
    podcast_uuid: str
    speaker_id: str
    voice_name: str

@app.post("/api/voices/set")
async def update_voice(data: VoiceUpdate, db: Session = Depends(get_db)):   
    global open_pc

    if open_pc is None:
        return {"status": "not found"}
    
    podcast = db.query(PodcastDB).filter(PodcastDB.id == data.podcast_uuid).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")      
    
    if not isinstance(podcast.voice_names, dict):
        podcast.voice_names = {}
    
    podcast.voice_names[int(data.speaker_id)] = data.voice_name   
    logging.info(f"Speaker: {data.speaker_id} is set to voice: {data.voice_name}") 
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating transcript: {e}")
    
    db.refresh(podcast)    
    open_pc.set_voice(int(data.speaker_id), data.voice_name)

    return {"status": "success"}

class DeleteVoiceRequest(BaseModel):
    filepath: str

@app.delete("/api/voices/delete")
def delete_voice(request: DeleteVoiceRequest):
    filepath = os.path.join(request.filepath)
    print(filepath)

    # Check if the file exists
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            logging.info(f"Deleted voice: {filepath}") 
        except Exception as e:
            raise HTTPException(status_code=500, detail="Could not delete file.")
        return {"detail": "File deleted successfully."}
    else:
        raise HTTPException(status_code=404, detail="File not found.")

def handle_interrupt(signum, frame) -> None:
    global is_shutdown, open_pc

    logging.info("Interrupt received, terminating app !!")
    is_shutdown = True
    open_pc.stop_all_threads()

def run_web_app() -> None:
    global open_pc

    signal.signal(signal.SIGINT, handle_interrupt)
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=2)

if __name__ == "__main__":   

    # init_logging()
    run_web_app()