from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Self
import soundfile as sf
import numpy as np
import io 

from omniai.core import Manifest
from omniai.core.base import BaseInput, BaseOutput


class SpeechModelInput(BaseInput):

    def asdict(
        self, 
    ):
        return asdict(self)


class VoiceInput(BaseInput):

    def __init__(
        self,
        voices: dict[str, np.ndarray]
    ):
        self._voices = voices 

    @staticmethod
    def load(
        manifest: Manifest
    ) -> Self:
        voices = VoiceInput.load_voices(
            path=manifest.backend.artifacts.voices.path 
        )

        return VoiceInput(
            voices=voices
        )

    @staticmethod
    def load_voices(
        path: str | Path,
    ) -> dict[str, np.ndarray]:
        
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Voice file not found: {path}")

        with np.load(path, allow_pickle=False) as data:
            return {
                voice_name: data[voice_name].copy()
                for voice_name in data.files
            }

    def voices(
        self, 
    ) -> list[str]:

        return list(self._voices.keys())

    def get(
        self, 
        voice: str
    ) -> np.ndarray:
        return self._voices[voice]



@dataclass
class AudioOutput(BaseOutput):
    audio: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=np.float32)
    )
    sample_rate: int = 24_000

    def add(self, output: Self) -> None:
        if self.sample_rate != output.sample_rate:
            raise ValueError(
                f"Sample-rate mismatch: "
                f"{self.sample_rate} != {output.sample_rate}"
            )

        self.audio = np.concatenate(
            (
                self.audio.reshape(-1),
                output.audio.reshape(-1),
            )
        )

    def save(self, path: str) -> None:
        sf.write(path, self.audio, self.sample_rate)

    def as_bytes(self) -> bytes:
        buffer = io.BytesIO()
        sf.write(
            buffer,
            self.audio,
            self.sample_rate,
            format="WAV",
        )
        return buffer.getvalue()