from functools import reduce
from typing import Self

from ..base import SpeechModel
from omniai.core import Manifest
from .processor import KokoroProcessor
from omniai.core.backends import ONNXBackend
from ..io import AudioOutput


class Kokoro(SpeechModel):

    def __init__(
        self,
        processor: KokoroProcessor,
        backend: ONNXBackend
    ):
        self.processor = processor
        self.backend = backend

    @staticmethod
    def load(
        manifest: Manifest, 
    ) -> Self:

        processor = KokoroProcessor.load(manifest=manifest)

        backend = ONNXBackend.load(
            model_path=manifest.backend.artifacts.model.path
        )

        return Kokoro(
            processor=processor, backend=backend
        )

    def close(self):
        self.backend.close()

    def voices(self) -> list[str]:
        return self.processor.voices()


    def create_stream(
        self, 
        text: str,
        voice: str = "af_heart"
    ):
        audio_map = map(
            lambda inputs: (
                AudioOutput(audio=self.backend.run(inputs=inputs.asdict()))
            ), self.processor.process(text=text, voice=voice)
        )

        return audio_map
    
    def create(
        self,
        text: str, 
        voice: str = "af_heart"
    ) -> AudioOutput:

        audio_map = map(
            lambda inputs: (
                AudioOutput(audio=self.backend.run(inputs=inputs.asdict()))
            ), self.processor.process(text=text, voice=voice)
        )

        return reduce(
            lambda audio1, audio2: (
                audio1.add(audio2)
            ), audio_map
        )