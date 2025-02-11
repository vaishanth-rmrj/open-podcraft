from dataclasses import dataclass, field, asdict

@dataclass
class DefaultConditioningParams:
    dnsmos_ovrl: int = 4
    vq_score: float = 0.78
    fmax: int = 22050
    pitch_std: int = 20
    speaking_rate: int = 15

@dataclass
class DefaultUnconditionParams:
    skip_speaker: bool = False
    skip_emotion: bool = False
    skip_vqscore_8: bool = True
    skip_fmax: bool = False
    skip_pitch_std: bool = False
    skip_speaking_rate: bool = False
    skip_dnsmos_ovrl: bool = True
    skip_speaker_noised: bool = False

@dataclass
class DefaultGenerationParams:
    cfg_scale: float = 1.0
    min_p: float = 0.2
    fmax: int = 22050
    seed: int = 421

@dataclass
class DefaultEmotionParams:
    happiness: float = 0.6
    sadness: float = 0.05
    disgust: float = 0.05
    fear: float = 0.05
    surprise: float = 0.1
    anger: float = 0.05
    other: float = 0.5
    neutral: float = 0.5

@dataclass
class DefaultConfig:
    uncondition_toggles: DefaultUnconditionParams = field(default_factory=DefaultUnconditionParams)
    conditioning_params: DefaultConditioningParams = field(default_factory=DefaultConditioningParams)
    generation_params: DefaultGenerationParams = field(default_factory=DefaultGenerationParams)
    emotion_params: DefaultEmotionParams = field(default_factory=DefaultEmotionParams)
    language_code: str = "en-us"
    model_type: str = "Zyphra/Zonos-v0.1-hybrid"