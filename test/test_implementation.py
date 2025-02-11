import os
import sys
import torch
import torchaudio
from datetime import datetime

# fix package path for imports to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from zonos.model import Zonos
from zonos.conditioning import make_cond_dict

# project imports
from utils.utils import process_script, check_available_voices

script_queue = []

process_script("assets/sample_podcast_script.txt", script_queue)


voices = check_available_voices("assets/voices")
print(voices)



# Use the hybrid with "Zyphra/Zonos-v0.1-hybrid"
model_type = ["Zyphra/Zonos-v0.1-hybrid", "Zyphra/Zonos-v0.1-transformer"]
model = Zonos.from_pretrained(model_type[0], device="cuda")
# TODO: test this
# model.bfloat16()
# model.eval()


output_dir = "outputs/" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
os.makedirs(output_dir, exist_ok=True)

line_counter = 0
for script_line in script_queue[:2]:

    if script_line.speaker == "Speaker 1":
        voice_filepath = voices["zonos_britishfemale"]
    
    if script_line.speaker == "Speaker 2":
        voice_filepath = voices["zonos_americanmale"]

    wav, sampling_rate = torchaudio.load(voice_filepath)
    speaker = model.make_speaker_embedding(wav, sampling_rate)

    torch.manual_seed(421)

    cond_dict = make_cond_dict(text=script_line.content, speaker=speaker, language="en-us")
    conditioning = model.prepare_conditioning(cond_dict)

    codes = model.generate(conditioning)

    wavs = model.autoencoder.decode(codes).cpu()
    print(type(wavs))
    torchaudio.save(os.path.join(output_dir, f"sample_{line_counter}.wav"), wavs[0], model.autoencoder.sampling_rate)
    line_counter += 1
