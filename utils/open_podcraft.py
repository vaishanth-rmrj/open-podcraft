import os
import sys
import torch
import torchaudio
from datetime import datetime
from typing import List, Dict
import logging
import time

# fix package path for imports to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from zonos.model import Zonos
from zonos.conditioning import make_cond_dict

# project imports
from utils import process_script, check_available_voices, ScriptLine, init_logging
from configs.utils import load_config
from configs.default import DefaultConfig

class OpenPodCraft:
    def __init__(self):
        
        self.podcast_speaker_queue = []

        self.config = load_config()
        self.available_voices = check_available_voices("assets/voices")
        
        # self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # TTS model from Zyphra
        self.model = Zonos.from_pretrained(self.config.model_type, device=self.device)
        self.model.bfloat16()
        self.model.eval()

        self.voices = {}
        self.audio_buffers = []
        self.silence_audio_path = "assets/voices/silence_100ms.wav"

        torch.manual_seed(421)
    
    def set_voice(self, speaker_id:int, voice_name:str):

        if not isinstance(speaker_id, int):
            raise ValueError(f"Speaker ID must be of type int but provided {type(speaker_id)}")

        if not voice_name in self.available_voices:
            raise ValueError(f"{voice_name} voice not found!!")
        
        self.voices[speaker_id] = voice_name
    
    def generate_chapters(self, files:List, context:str, prompt:str) -> str:
        raise NotImplementedError("Generating chapters from files not yet implemented !!")
    
    def generate_podcast_script(self, chapters:str, prompt:str):
        raise NotImplementedError("Generating podcast script from chapters not yet implemented !!")

    def fetch_speaker_info(self, speaker_queue:List[ScriptLine]):
        """
        checks for speakers and asigned voices in the queue

        Args:
            speaker_queue (List[ScriptLine]): sequence of lines in the podcast corresponding to each speaker

        Returns:
            int, list: no. of sepakers, list of voice names
        """

        ids = set()
        voice_names = set()
        for script_line in speaker_queue:
            if script_line.speaker_id not in self.voices:
                raise ValueError(f"Speaker ID : {script_line.speaker_id} is not present in voices you have set! {self.voices}")
            
            if not script_line.speaker_id in ids:
                ids.add(script_line.speaker_id)
                voice_names.add(self.voices[script_line.speaker_id])
        
        return len(ids), voice_names
    
    def get_speaker_embedding(self, voice_filepath, model, device:torch.device):
        """
        get the speaker embedding from voice file (.wav, .mp3) 
        to be used for audio generation

        Args:
            voice_filepath (str): path where voice file is stored
            model (_type_): zonos model
            device (torch.device): device

        Returns:
            _type_: speaker embedding
        """
        wav, sampling_rate = torchaudio.load(voice_filepath)
        speaker_embedding = model.make_speaker_embedding(wav, sampling_rate)    
        speaker_embedding = speaker_embedding.to(device)  
        return speaker_embedding

    def get_speaker_embeddings_and_params(self, voice_names, configs:Dict):

        if len(voice_names) == 0:
            raise ValueError(f"No voice names provided")
        
        if not isinstance(configs, Dict):
            raise ValueError(f"Expected configs to be of type {type(dict)}")
        
        if not len(voice_names) == len(configs.keys()):
            raise ValueError(f"Not matching !! Provided voice names: {voice_names}. Provided voice config: {configs.keys()}")

        speakers_embedding = {}
        speakers_params = {}
        for id, voice in enumerate(voice_names):
            speakers_embedding[voice] = self.get_speaker_embedding(
                str(self.available_voices[voice]),
                self.model,
                self.device,
            )

            config = configs[voice]
            speakers_params[voice] = {}
            # speakers_params[voice]["emotion_tensor"] = torch.tensor(
            #     [[
            #         float(config.emotion_params.happiness), 
            #         float(config.emotion_params.sadness), 
            #         float(config.emotion_params.disgust), 
            #         float(config.emotion_params.fear), 
            #         float(config.emotion_params.surprise), 
            #         float(config.emotion_params.anger), 
            #         float(config.emotion_params.other), 
            #         float(config.emotion_params.neutral)
            #     ]], 
            #         device=self.device
            # )

            vq_val = float(config.conditioning_params.vq_score)
            speakers_params[voice]["vq_tensor"] = torch.tensor([vq_val] * 8, device=self.device).unsqueeze(0)

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
            
            speakers_params[voice]["uncond_keys"] = uncond_keys

            speakers_params[voice]["fmax"]=config.conditioning_params.fmax
            speakers_params[voice]["pitch_std"]=config.conditioning_params.pitch_std
            speakers_params[voice]["speaking_rate"]=config.conditioning_params.speaking_rate
            speakers_params[voice]["dnsmos_ovrl"]=config.conditioning_params.dnsmos_ovrl
            speakers_params[voice]["speaker_noised_bool"]=config.speaker_noised_bool
            speakers_params[voice]["language_code"]=config.language_code

        return speakers_embedding, speakers_params
    
    def get_audio_prefix(self, prefix_audio_path: str, overlap_time_ms: int = 100):
        """
        audio prefix is used for smooth transitioning of audio chunks

        Args:
            prefix_audio_path (str): path to prefix audio file
            overlap_time_s (float, optional): amount of time to overlap previous audio chunk. Defaults to 1.0.

        Returns:
            _type_: audio_prefix_codes
        """

        # get metadata of the audio file
        metadata = torchaudio.info(prefix_audio_path)
        sample_rate, num_frames = metadata.sample_rate, metadata.num_frames 

        # Calculate the frame offset to start loading from the last overlap_time_ms milliseconds
        frame_offset = max(0, num_frames - int((overlap_time_ms / 1000) * sample_rate))

        # load prefix audio with last overlap_time_s
        wav_prefix, sr_prefix = torchaudio.load(prefix_audio_path, frame_offset=frame_offset)
        wav_prefix = wav_prefix.mean(0, keepdim=True)
        wav_prefix = torchaudio.functional.resample(wav_prefix, sr_prefix, self.model.autoencoder.sampling_rate)
        wav_prefix = wav_prefix.to(self.device, dtype=torch.float32)

        with torch.autocast(self.device, dtype=torch.float32):
            audio_prefix_codes = self.model.autoencoder.encode(wav_prefix.unsqueeze(0))
        
        return audio_prefix_codes

    def generate_podcast(
            self, 
            speaker_queue:List[ScriptLine],            
            output_dir:str,
            audio_overlap_duration_ms: int = 100,
        ):

        num_speakers, voice_names = self.fetch_speaker_info(speaker_queue)
        logging.info(f"{num_speakers} speakers are used in the podcast with the following voices {voice_names}")

        # make speakerembedding for each unique voice
        # TODO: make speaker params unique for each speaker
        # TODO: time this section
        configs = {voice_name: self.config for voice_name in voice_names}
        speakers_embedding, speakers_params = self.get_speaker_embeddings_and_params(
            voice_names, configs
        )
        
        # generating voice over for each line in the script
        prefix_audio_path = self.silence_audio_path
        self.audio_buffers = []
        for line_id, speaker_line in enumerate(speaker_queue):
            logging.info(f"Performing voice over for podcast script line: {line_id}")
            start_t = time.perf_counter()
            voice_name = self.voices[speaker_line.speaker_id]
            speaker_embedding = speakers_embedding[voice_name]
            voice_config = speakers_params[voice_name]

            emotion_tensor = torch.tensor(
                [[
                    float(speaker_line.emotions_arr[0]), 
                    float(speaker_line.emotions_arr[1]), 
                    float(speaker_line.emotions_arr[2]), 
                    float(speaker_line.emotions_arr[3]), 
                    float(speaker_line.emotions_arr[4]), 
                    float(speaker_line.emotions_arr[5]), 
                    float(0.1), 
                    float(0.1)
                ]], 
                    device=self.device
            )
            
            print(f"Emotion tensor: {emotion_tensor}")
            cond_dict = make_cond_dict(
                text=speaker_line.content,
                language=voice_config["language_code"],
                speaker=speaker_embedding,
                emotion=emotion_tensor,
                vqscore_8=voice_config["vq_tensor"],
                fmax=voice_config["fmax"],
                pitch_std=voice_config["pitch_std"],
                speaking_rate=voice_config["speaking_rate"],
                dnsmos_ovrl=voice_config["dnsmos_ovrl"],
                speaker_noised=voice_config["speaker_noised_bool"],
                device=self.device,
                unconditional_keys=voice_config["uncond_keys"],
            )
            conditioning = self.model.prepare_conditioning(cond_dict)

            audio_prefix_codes = self.get_audio_prefix(prefix_audio_path, audio_overlap_duration_ms)
            # generating the audio
            codes = self.model.generate(
                prefix_conditioning=conditioning,
                audio_prefix_codes=audio_prefix_codes,
                # max_new_tokens=max_new_tokens,
                # cfg_scale=config.generation_params.cfg_scale,
                # batch_size=1,
                # sampling_params=dict(min_p=config.generation_params.min_p),
            )

            wavs = self.model.autoencoder.decode(codes).cpu()
            if line_id > 0:
                overlap_slice_index = int((audio_overlap_duration_ms / 1000) * self.model.autoencoder.sampling_rate)
                self.audio_buffers.append(wavs[0][:, overlap_slice_index:])
            else:
                self.audio_buffers.append(wavs[0])

            audio_save_path = os.path.join(output_dir, f"seq_{line_id}.wav")
            torchaudio.save(audio_save_path, wavs[0], self.model.autoencoder.sampling_rate)
            prefix_audio_path = audio_save_path
            logging.info(f"Completed voice over for podcast script line: {line_id} in {time.perf_counter()-start_t}s")

        final_audio= torch.cat(self.audio_buffers, dim=-1)
        self.audio_buffers = [] # clear audio buffer
        torchaudio.save(os.path.join(output_dir, "final.wav"), final_audio, self.model.autoencoder.sampling_rate)
        logging.info(f"Saving the entire podcast to: {os.path.join(output_dir, 'final.wav')}")

if __name__ == "__main__":

    init_logging()

    podcast_speaker_queue = []
    process_script("assets/sample_3.txt", podcast_speaker_queue)

    open_pc = OpenPodCraft()
    
    # set voices
    open_pc.set_voice(1, "zonos_americanmale")
    open_pc.set_voice(2, "zonos_britishfemale")

    output_dir = "outputs/" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(output_dir, exist_ok=True)

    # generate podcast
    open_pc.generate_podcast(podcast_speaker_queue, output_dir=output_dir)