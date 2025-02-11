import os
import sys
import torch
import torchaudio
from datetime import datetime
from typing import List

# fix package path for imports to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from zonos.model import Zonos
from zonos.conditioning import make_cond_dict

# project imports
from utils.utils import process_script, check_available_voices, ScriptLine
from configs.utils import load_config
from configs.default import DefaultConfig

config = load_config()

script_queue = []
process_script("assets/sample_podcast_script.txt", script_queue)

voices = check_available_voices("assets/voices")

# Use the hybrid with "Zyphra/Zonos-v0.1-hybrid"
# model_type = ["Zyphra/Zonos-v0.1-hybrid", "Zyphra/Zonos-v0.1-transformer"]
model = Zonos.from_pretrained(config.model_type, device="cuda")
# TODO: test this
model.bfloat16()
model.eval()

output_dir = "outputs/" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
os.makedirs(output_dir, exist_ok=True)

# dev only
for script_line in script_queue:
    if script_line.speaker == "Speaker 1":
        # script_line.speaker = "zonos_britishfemale"
        script_line.speaker = "zonos_americanmale"
    
    if script_line.speaker == "Speaker 2":
        # script_line.speaker = "zonos_americanmale"
        script_line.speaker = "zonos_britishfemale"


def generate_script_voice_overs(
        script_queue: List[ScriptLine],
        model,
        voices: dict,
        config: DefaultConfig,
        output_dir: str,
        verbose: bool = True,
        device: str = "cuda",
        max_new_tokens: float = 86 * 30
    ) -> None:

    torch.manual_seed(421)
    line_counter = 0
    prefix_audio_path = "assets/voices/silence_100ms.wav"
    accumulated_audio = []

    overlap_duration = 1  # 1-second overlap
    sampling_rate = model.autoencoder.sampling_rate  # Get model's sampling rate
    overlap_samples = int(overlap_duration * sampling_rate)  # Convert seconds to samples


    for script_line in script_queue:
        
        print(f"Speaker: {script_line.speaker}, content: {script_line.content}")
        # create speaker embeding for unique voices
        voice_filepath = voices[script_line.speaker]
        wav, sampling_rate = torchaudio.load(voice_filepath)
        # speaker_embedding = model.embed_spk_audio(wav, sampling_rate)   
        speaker_embedding = model.make_speaker_embedding(wav, sampling_rate)    
        speaker_embedding = speaker_embedding.to(device, dtype=torch.bfloat16)   

        # add prefix audio to the generation for smoother transitions
        audio_prefix_codes = None
        if prefix_audio_path is not None:

            # Get metadata of the audio file
            n_seconds = 1
            metadata = torchaudio.info(prefix_audio_path)
            sample_rate = metadata.sample_rate  # Sampling rate of the audio
            num_frames = metadata.num_frames  # Total frames in the audio

            # Calculate the frame offset to start loading from the last n seconds
            frame_offset = max(0, num_frames - n_seconds * sample_rate)

            wav_prefix, sr_prefix = torchaudio.load(prefix_audio_path, frame_offset=frame_offset)
            wav_prefix = wav_prefix.mean(0, keepdim=True)
            wav_prefix = torchaudio.functional.resample(wav_prefix, sr_prefix, model.autoencoder.sampling_rate)
            wav_prefix = wav_prefix.to(device, dtype=torch.float32)
            with torch.autocast(device, dtype=torch.float32):
                audio_prefix_codes = model.autoencoder.encode(wav_prefix.unsqueeze(0))

        emotion_tensor = torch.tensor(
            [[
                float(config.emotion_params.happiness), 
                float(config.emotion_params.sadness), 
                float(config.emotion_params.disgust), 
                float(config.emotion_params.fear), 
                float(config.emotion_params.surprise), 
                float(config.emotion_params.anger), 
                float(config.emotion_params.other), 
                float(config.emotion_params.neutral)
            ]], 
                device=device
        )

        vq_val = float(config.conditioning_params.vq_score)
        vq_tensor = torch.tensor([vq_val] * 8, device=device).unsqueeze(0)

        uncond_keys = []
        if config.uncondition_toggles.skip_speaker:
            uncond_keys.append("speaker")
        if config.uncondition_toggles.skip_emotion:
            uncond_keys.append("emotion")
        if config.uncondition_toggles.skip_vqscore_8:
            uncond_keys.append("vqscore_8")
        if config.uncondition_toggles.skip_fmax:
            uncond_keys.append("fmax")
        if config.uncondition_toggles.skip_pitch_std:
            uncond_keys.append("pitch_std")
        if config.uncondition_toggles.skip_speaking_rate:
            uncond_keys.append("speaking_rate")
        if config.uncondition_toggles.skip_dnsmos_ovrl:
            uncond_keys.append("dnsmos_ovrl")
        if config.uncondition_toggles.skip_speaker_noised:
            uncond_keys.append("speaker_noised")

        # cond_dict = make_cond_dict(text=script_line.content, speaker=speaker_embedding, language=config.language_code)
        cond_dict = make_cond_dict(
            text=script_line.content,
            language=config.language_code,
            speaker=speaker_embedding,
            emotion=emotion_tensor,
            vqscore_8=vq_tensor,
            fmax=config.conditioning_params.fmax,
            pitch_std=config.conditioning_params.pitch_std,
            speaking_rate=config.conditioning_params.speaking_rate,
            dnsmos_ovrl=config.conditioning_params.dnsmos_ovrl,
            speaker_noised=config.speaker_noised_bool,
            device=device,
            unconditional_keys=uncond_keys,
        )
        conditioning = model.prepare_conditioning(cond_dict)
        # generating the audio
        # codes = model.generate(conditioning)
        codes = model.generate(
            prefix_conditioning=conditioning,
            audio_prefix_codes=audio_prefix_codes,
            # max_new_tokens=max_new_tokens,
            # cfg_scale=config.generation_params.cfg_scale,
            batch_size=1,
            # sampling_params=dict(min_p=config.generation_params.min_p),
        )

        wavs = model.autoencoder.decode(codes).cpu()

        if line_counter > 0:
            accumulated_audio.append(wavs[0][:, overlap_samples:])
        else:
            accumulated_audio.append(wavs[0])

        audio_save_path = os.path.join(output_dir, f"sample_{line_counter}.wav")
        torchaudio.save(audio_save_path, wavs[0], model.autoencoder.sampling_rate)
        prefix_audio_path = audio_save_path
        line_counter += 1
    
    final_audio= torch.cat(accumulated_audio, dim=-1)
    torchaudio.save(os.path.join(output_dir, "final.wav"), final_audio, model.autoencoder.sampling_rate)


generate_script_voice_overs(
    script_queue=script_queue,
    model=model,
    voices=voices,
    config=config,
    output_dir=output_dir,
    verbose=True,
    device="cuda"
)