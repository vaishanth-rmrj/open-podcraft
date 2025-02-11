from pathlib import Path
from pydantic import BaseModel

class ScriptLine(BaseModel):
    speaker: str
    speaker_id: int = 0
    content: str


def process_script(script_filepath: str, queue: list[ScriptLine]) -> None:
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
            queue.append(
                ScriptLine(speaker=speaker.strip(), content=content.strip())
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
