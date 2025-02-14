import os
from pathlib import Path
import sys
import torch
import torchaudio
from datetime import datetime
from typing import List, Dict
import logging
import time
import threading
from dotenv import load_dotenv

# fix package path for imports to work
sys.path.append(str(Path(__file__).resolve().parent.parent))

from openai import OpenAI
from zonos.model import Zonos
from zonos.conditioning import make_cond_dict

# project imports
from utils.util import process_script_from_txt, check_available_voices, ScriptLine, setup_logging, load_prompts, process_podcast_script_from_llm
from configs.utils import load_config
from configs.default import DefaultConfig

load_dotenv()  # loads variables from .env
setup_logging()

class OpenPodCraft:
    def __init__(self):

        logging.info("Initializing OpenPodCraft...")
        
        self.podcast_speaker_queue = []
        self.chapters = None
        prompts = load_prompts()
        self.curr_prompt = prompts[0]
        self.curr_podcast_uuid = None

        self.config = load_config()
        self.available_voices = check_available_voices("assets/voices")
        
        # self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.llm_model_type = "deepseek/deepseek-chat:free" #"deepseek/deepseek-r1:free"

        # TTS model from Zyphra
        logging.info(f"Initializing TTS model: {self.config.model_type}")
        self.model = Zonos.from_pretrained(self.config.model_type, device=self.device)
        self.model.bfloat16()
        self.model.eval()

        self.voices = {}
        self.audio_buffers = []
        self.silence_audio_path = "assets/voices/silence_100ms.wav"

        self.thread_queue = []
        self.flags = {
            "is_generating_script": False,
            "is_script_available": False,
            "is_generating_podcast": False,
            "is_podcast_available": False,
            "interupt_generation": False
        }
        self.user_prompt = None
        self.num_speakers = 2
        self.podcast_len = 10 # mins

        # TODO: imeplement gui to change this
        # setting default voices
        self.set_voice(1, "zonos_americanmale")
        self.set_voice(2, "zonos_britishfemale")

        torch.manual_seed(421)
    
    def reset(self):
        """
        reset the podcast info stored in variables
        """

        self.podcast_speaker_queue = []
        self.chapters = None
        self.curr_podcast_uuid = None

        self.available_voices = check_available_voices("assets/voices")
        self.audio_buffers = []

        self.flags = {
            "is_generating_script": False,
            "is_script_available": False,
            "is_generating_podcast": False,
            "is_podcast_available": False,
            "interupt_generation": False
        }

    
    def set_voice(self, speaker_id:int, voice_name:str):

        if not isinstance(speaker_id, int):
            raise ValueError(f"Speaker ID must be of type int but provided {type(speaker_id)}")

        if not voice_name in self.available_voices:
            raise ValueError(f"{voice_name} voice not found!!")
        
        self.voices[speaker_id] = voice_name
    
    def get_podcast_script_as_dict(self) -> List[Dict]:
        logging.info(f"logging getting stranscript for : {self.curr_podcast_uuid}")
        queue = []
        for script_line in self.podcast_speaker_queue:
            queue.append(
                {
                    "speaker": script_line.speaker,
                    "speaker_id": script_line.speaker_id,
                    "content": script_line.content,
                    "emotion_arr": script_line.emotions_arr
                }
            )
        logging.info(queue)
        return queue      

    def set_podcast_script_from_dict(self, dict_script_queue:List[Dict]) -> None:

        if len(dict_script_queue) > 0:
            self.podcast_speaker_queue = []
            for script_dict in dict_script_queue:
                self.podcast_speaker_queue.append(
                    ScriptLine(
                        speaker = script_dict["speaker"],
                        speaker_id = script_dict["speaker_id"],
                        content = script_dict["content"],
                        emotions_arr = script_dict["emotion_arr"],
                    )
                )  

            self.flags["is_script_available"]  = True 
    
    def generate_chapters(self, files:List, context:str, prompt:str) -> str:
        raise NotImplementedError("Generating chapters from files not yet implemented !!")
    
    def generate_podcast_script(
            self, 
            chapters:str, 
            prompt:str,
            user_prompt:str = None, 
            podcast_len:int = 10,
            num_speakers:int = 2,
            llm_model_type:str = "deepseek/deepseek-r1:free"
        ):

        logging.info(f"Generating podcast script from API using model :{llm_model_type}")

        self.podcast_speaker_queue = []
        self.flags["is_script_available"] = False 
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise EnvironmentError("The OPENROUTER_API_KEY environment variable is not set.")

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        if user_prompt is None:
            user_prompt = "No additonal requirements"

        # create msg
        msgs = [
            {
                "role": "user",
                "content": f"Chapters: \n {chapters} \n end of chapters"
            },
            {
                "role": "user",
                "content": f"rules: \n {prompt['rules']} PodcastDuration: {str(podcast_len)} minutes (strict) No of speaker: {str(num_speakers)} \n end of rules"
            },
            {
                "role": "user",
                "content": f"Prompt: \n {prompt['context']} \n Additonal Requirements (strict): {str(user_prompt)} \n \n end of prompt"
            }
        ]

        logging.info(f"Requested response from: {str(llm_model_type)}")
        logging.info("Waiting for LLM response. Please wait it might take several minutes !!")
        self.flags["is_generating_script"] = True
        completion = client.chat.completions.create(
            extra_headers={
                # "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "Open-PodCraft", # Optional. Site title for rankings on openrouter.ai.
            },
            extra_body={},
            model=llm_model_type,
            messages=msgs,
        )
        logging.info("LLM response received")

        llm_response = completion.choices[0].message.content
        if llm_response is None or len(llm_response) < 2:
            logging.info(f"Did not receive a response from LLM. Try again !!")
            self.flags["is_generating_script"] = False
            return False

        # generate podcast script speaker queue  from raw llm response
        process_podcast_script_from_llm(
            llm_response,
            queue = self.podcast_speaker_queue,
        )

        self.flags["is_script_available"] = True if len(self.podcast_speaker_queue) > 0 else False
        self.flags["is_generating_script"] = False

        print(self.podcast_speaker_queue)
        self.thread_queue.pop()
        return True

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
        self.flags["is_generating_podcast"] = True
        self.flags["is_podcast_available"] = False
        for line_id, speaker_line in enumerate(speaker_queue):
            logging.info(f"Performing voice over for podcast script line: {line_id}")

            if self.flags["interupt_generation"]:
                self.flags["interupt_generation"] = False
                return

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

            if self.flags["interupt_generation"]:
                self.flags["interupt_generation"] = False
                return

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
        self.flags["is_generating_podcast"] = False
        self.flags["is_podcast_available"] = True

        self.thread_queue.pop()
    
    def run_in_thread(self, fn_name:str) -> bool:

        if len(self.thread_queue) > 0:
            logging.info("Background threads running. Please stop other threads / processes !!")
            return False

        if fn_name == "generate_podcast_script":
            if self.chapters is None:
                logging.info(f"Chapters not found!! Try adding chapters fist.")
                return False
            
            thread = threading.Thread(
                target=self.generate_podcast_script,
                args=[self.chapters, self.curr_prompt, self.user_prompt, self.podcast_len, self.num_speakers,  self.llm_model_type],
                daemon=True, 
            )
        
        elif fn_name == "generate_podcast":
            if len(self.podcast_speaker_queue) == 0:
                logging.info(f"No prodcast script in queue!! Did you generate the script ?")
                return False

            output_dir = os.path.join("static", "audio_outputs", "podcast-"+str(self.curr_podcast_uuid))
            # output_dir = "outputs/" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            os.makedirs(output_dir, exist_ok=True)
            
            thread = threading.Thread(
                target=self.generate_podcast,
                args=[self.podcast_speaker_queue, output_dir],
                daemon=True, 
            )
        
        else:
            logging.info(f"Unknown function provided: {fn_name}")
            return False

        # start the thread and store it
        self.thread_queue.append(thread)
        thread.start()
        return True

    def stop_all_threads(self):
        active_threads = len(self.thread_queue)
        if active_threads > 0:
            logging.info(f"{active_threads} background threads running. Terminating all threads !!")

            for thread in self.thread_queue:
                thread.join()
                del thread           
            
        else:
            logging.info(f"stop_threads : No background threads running. XD")
                
        return True if len(self.thread_queue) == 0 else False
      

if __name__ == "__main__":

    # init_logging()

    # load chapters
    with open("assets/chapters.txt", "r") as f:
        chapters = f.read()
    
    prompts = load_prompts()
    prompt = prompts[0]

    open_pc = OpenPodCraft()
    
    # set voices
    open_pc.set_voice(1, "zonos_americanmale")
    open_pc.set_voice(2, "zonos_britishfemale")

    output_dir = "outputs/" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(output_dir, exist_ok=True)

    # generate and process popcast script
    open_pc.generate_podcast_script(chapters, prompt)

    # # generate podcast
    open_pc.generate_podcast(open_pc.podcast_speaker_queue, output_dir=output_dir)