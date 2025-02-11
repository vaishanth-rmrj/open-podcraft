from pathlib import Path
from pydantic import BaseModel
import re
import logging
from datetime import datetime

class ScriptLine(BaseModel):
    speaker: str
    speaker_id: int = 0
    content: str


def process_script(script_filepath: str, queue: list[ScriptLine], speaker_match_expr:str = r"Speaker\s+(\S+)") -> None:
    """
    process the script file to extract the speaker and content
    """
    # load the script file
    with open(script_filepath, "r") as f:
        script_lines = f.readlines()

    for line in script_lines:
        if not line:
            continue
        
        # TODO: make it robust to script speaker name variations
        # for now should do the work
        # check if the line contains a colon to separate speaker ID and content
        if ":" in line:
            # split only at the first colon in case the content also contains colons
            speaker, content = line.split(":", 1)
            match = re.match(speaker_match_expr, speaker)
            if not match:
                raise ValueError(f"Invalid speaker str provided: {speaker}")
            
            queue.append(
                ScriptLine(speaker=speaker.strip(), speaker_id=int(match.group(1)), content=content.strip())
            )

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