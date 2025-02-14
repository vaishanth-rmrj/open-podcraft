from pathlib import Path
from pydantic import BaseModel
import re
import ast
import logging
from datetime import datetime
import yaml

from typing import List, Dict

class ScriptLine(BaseModel):
    speaker: str
    speaker_id: int = 0
    content: str
    emotions_arr: List = []


def process_podcast_script_from_llm(llm_response: str, queue: list[ScriptLine]) -> None:
    """
    process the response from llm to extract the speaker and content for the podcast script
    """

    llm_response_list = llm_response.split("\n")
    print(llm_response_list)
    
    speaker_pattern = r"Speaker\s+(\d+):"
    emotion_pattern = r"Emotion:\s*(\[[^\]]+\])"
    context_pattern = r"context:\s*(.+)"

    for line in llm_response_list:
        if not line:
            continue

        # Extract speaker ID
        speaker_match = re.search(speaker_pattern, line)
        speaker_id = speaker_match.group(1) if speaker_match else None

        # Extract emotion list string and convert it to an actual Python list
        emotion_match = re.search(emotion_pattern, line)
        if emotion_match:
            emotion_list_str = emotion_match.group(1)
            # Safely evaluate the list string to a Python list
            emotion_list = ast.literal_eval(emotion_list_str)
        else:
            emotion_list = None

        # Extract context
        context_match = re.search(context_pattern, line)
        context = context_match.group(1).strip() if context_match else None
        
        # TODO: make it robust to script speaker name variations
        # for now should do the work
        # check if the line contains a colon to separate speaker ID and content
        if speaker_id is not None or context is not None:
            queue.append(
                ScriptLine(
                    speaker=f"Speaker {speaker_id}", 
                    speaker_id=int(speaker_id), 
                    content=context.strip(),
                    emotions_arr=emotion_list,
                )
            )

def process_script_from_txt(script_filepath: str, queue: list[ScriptLine], speaker_match_expr:str = r"Speaker\s+(\S+)") -> None:
    """
    process the script file to extract the speaker and content
    """
    # load the script file
    with open(script_filepath, "r") as f:
        script_lines = f.readlines()
    
    speaker_pattern = r"Speaker\s+(\d+):"
    emotion_pattern = r"Emotion:\s*(\[[^\]]+\])"
    context_pattern = r"context:\s*(.+)"

    for line in script_lines:
        if not line:
            continue

        # Extract speaker ID
        speaker_match = re.search(speaker_pattern, line)
        speaker_id = speaker_match.group(1) if speaker_match else None

        # Extract emotion list string and convert it to an actual Python list
        emotion_match = re.search(emotion_pattern, line)
        if emotion_match:
            emotion_list_str = emotion_match.group(1)
            # Safely evaluate the list string to a Python list
            emotion_list = ast.literal_eval(emotion_list_str)
        else:
            emotion_list = None

        # Extract context
        context_match = re.search(context_pattern, line)
        context = context_match.group(1).strip() if context_match else None
        
        # TODO: make it robust to script speaker name variations
        # for now should do the work
        # check if the line contains a colon to separate speaker ID and content
        if speaker_id is not None or context is not None:
            queue.append(
                ScriptLine(
                    speaker=f"Speaker {speaker_id}", 
                    speaker_id=int(speaker_id), 
                    content=context.strip(),
                    emotions_arr=emotion_list,
                )
            )
        # if ":" in line:
        #     # split only at the first colon in case the content also contains colons
        #     speaker, content = line.split(":", 1)
        #     match = re.match(speaker_match_expr, speaker)
        #     if not match:
        #         raise ValueError(f"Invalid speaker str provided: {speaker}")
            
        #     queue.append(
        #         ScriptLine(speaker=speaker.strip(), speaker_id=int(match.group(1)), content=content.strip())
        #     )

def check_available_voices(dir_path: str):
    voices = {}
    directory = Path(dir_path)
    for file in directory.iterdir():
        if file.is_file() and file.suffix.lower() in [".wav", ".mp3"]:
            voices[file.stem] = str(file)            
            # voices.append({
            #     "voice_name": file.stem,
            #     "path": str(file)
            # })
    return voices

def get_speaker_id(text:str, match_expr:str = r"Speaker\s+(\S+)"):
    match = re.match(match_expr, text)
    if match:
        return int(match.group(1))
    
    raise ValueError(f"Invalid speaker str provided: {text}")

class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_list = []

    def emit(self, record):
        log_entry = self.format(record)
        self.log_list.append(log_entry)

# Function to initialize logging
def init_logging():
    def custom_format(record):
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fnameline = f"{record.pathname}:{record.lineno}"
        message = f"{record.levelname} {dt} {fnameline[-15:]:>15} {record.msg}"
        return message

    # Reset root handlers
    logging.basicConfig(level=logging.INFO)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create a formatter that uses custom_format
    formatter = logging.Formatter()
    formatter.format = custom_format

    # Console handler for logging to terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Custom ListHandler to store logs in a list
    list_handler = ListHandler()
    list_handler.setFormatter(formatter)

    # Add handlers to the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(list_handler)

    # Return the list handler for later use
    return list_handler

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

def load_prompts(filename:str = "assets/prompts.yaml"):
    with open(filename, "r") as file:
        prompts = yaml.safe_load(file)
    return prompts

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