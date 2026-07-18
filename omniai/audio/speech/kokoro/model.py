from typing import Self, Generator

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
    ) -> Generator:
        
        yield from map(
            lambda inputs: (
                AudioOutput(audio=self.backend.run(inputs=inputs.asdict()))
            ), self.processor.process(text=text, voice=voice)
        )
    
    def create(
        self,
        text: str, 
        voice: str = "af_heart"
    ) -> AudioOutput:

        output = AudioOutput()

        for chunk in self.create_stream(text=text, voice=voice):
            output.add(chunk)

        return output
