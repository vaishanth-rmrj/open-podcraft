import logging
import os
import json
from dataclasses import dataclass, field, asdict

# project imports
from configs.default import DefaultConfig, DefaultUnconditionParams, DefaultConditioningParams, DefaultGenerationParams, DefaultEmotionParams

def save_config(config: DefaultConfig, filename: str = "configs/default.json"):
    """
    save / cache config for later use
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    logging.info(f"Saving config to {filename}")
    with open(filename, 'w') as f:
        json.dump(asdict(config), f, indent=4)

def load_config():
    """
    load the configuration
    """

    config_path = "configs/default.json"
    if os.path.exists(config_path):
        logging.info(f"Loading config from {config_path}")
        with open(config_path, "r") as f:
            data = json.load(f)
        
        return DefaultConfig(
            uncondition_toggles=DefaultUnconditionParams(**data.get("uncondition_toggles", {})),
            conditioning_params=DefaultConditioningParams(**data.get("conditioning_params", {})),
            generation_params=DefaultGenerationParams(**data.get("generation_params", {})),
            emotion_params=DefaultEmotionParams(**data.get("emotion_params", {})),
            language_code=data.get("language_code", "en-us"),
            model_type=data.get("model_type", "Zyphra/Zonos-v0.1-hybrid"),
            speaker_noised_bool=data.get("speaker_noised_bool", False)
        )

    logging.info(f"Config file not found at {config_path}. Creating a new one.")
    default_config = DefaultConfig()
    save_config(default_config, filename=config_path)
    return default_config