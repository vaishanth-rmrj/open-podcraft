from dataclasses import dataclass, field, asdict

@dataclass
class DefaultConditioningParams:
    dnsmos_ovrl: int = 3
    vq_score: float = 0.72
    fmax: int = 22050
    pitch_std: int = 300
    speaking_rate: int = 15

@dataclass
class DefaultUnconditionParams:
    skip_speaker: bool = False
    skip_emotion: bool = False
    skip_vqscore_8: bool = False
    skip_fmax: bool = False
    skip_pitch_std: bool = False
    skip_speaking_rate: bool = True
    skip_dnsmos_ovrl: bool = False
    skip_speaker_noised: bool = False

@dataclass
class DefaultGenerationParams:
    cfg_scale: float = 3.5
    min_p: float = 0.0
    seed: int = 420

@dataclass
class DefaultEmotionParams:
    happiness: float = 0.6
    sadness: float = 0.05
    disgust: float = 0.05
    fear: float = 0.05
    surprise: float = 0.05
    anger: float = 0.05
    other: float = 0.05
    neutral: float = 0.05

@dataclass
class DefaultConfig:
    uncondition_toggles: DefaultUnconditionParams = field(default_factory=DefaultUnconditionParams)
    conditioning_params: DefaultConditioningParams = field(default_factory=DefaultConditioningParams)
    generation_params: DefaultGenerationParams = field(default_factory=DefaultGenerationParams)
    emotion_params: DefaultEmotionParams = field(default_factory=DefaultEmotionParams)
    language_code: str = "en-us"
    model_type: str =  "Zyphra/Zonos-v0.1-hybrid" #"Zyphra/Zonos-v0.1-transformer"
    speaker_noised_bool: bool = False