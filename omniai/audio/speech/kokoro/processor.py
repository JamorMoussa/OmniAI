from dataclasses import dataclass 
import numpy as np 
import phonemizer
import json 
import re

from omniai.core.base import OmniAIBaseProcessor
from ..io import SpeechModelInput, VoiceInput
from omniai.core import Manifest


@dataclass 
class KokoroInput(SpeechModelInput):
    tokens: np.ndarray
    style: np.ndarray
    speed: np.ndarray
    text: str

    def asdict(self):
        inputs = super().asdict()
        inputs.pop("text")
        return inputs


@dataclass
class Vocab:
    _dict: dict[str, int]

    @classmethod
    def load(
        cls, 
        manifest: Manifest
    ):
        with open(
            manifest.backend.artifacts.vocab.path, "r", encoding="utf-8"
        ) as f:
            vocab = json.load(f)

        return cls(_dict = vocab["vocab"])

    def get(
        self, key: str
    ):
        return self._dict.get(key)

    def keys(self):
        return self._dict.keys()


class KokoroProcessor(OmniAIBaseProcessor):

    def __init__(
        self,
        voice_inpt: VoiceInput, 
        vocab: Vocab
    ):
        super().__init__()

        self.voice_inpt = voice_inpt
        self.vocab = vocab

    def voices(
        self, 
    ) -> list[str]:
        return self.voice_inpt.voices()


    @staticmethod
    def load(
        manifest: Manifest
    ):
        voice_inpt = VoiceInput.load(
            manifest=manifest
        )

        vocab = Vocab.load(manifest=manifest)

        return KokoroProcessor(
            voice_inpt=voice_inpt, vocab=vocab
        )
    
    def _tokenize(
        self, 
        phonemes: str,
        vocab: Vocab
    ) -> list[int]:
        
        phonemes = re.sub(r"\s+", " ", phonemes.strip())

        tokens = []

        for c in phonemes:
            token = vocab.get(c)

            if token is not None:
                tokens.append(token)

        return tokens

    def _phonemize(
        self, 
        text: str,
        lang: str = "en-us"
    ) -> str:
        return phonemizer.phonemize(
            text,
            language=lang,
            preserve_punctuation=True,
            with_stress=True,
        )


    def _split_text(
        self, 
        text: str,
        max_chars: int = 510,
        preferred_separators: str = r"[.!?;,،؛:]",
    ) -> list[str]:

        if not text or not text.strip():
            return []

        # Normalize repeated whitespace.
        text = re.sub(r"\s+", " ", text).strip()

        chunks: list[str] = []
        remaining = text

        while len(remaining) > max_chars:
            window = remaining[: max_chars + 1]

            punctuation_matches = list(re.finditer(preferred_separators, window))

            if punctuation_matches:
                split_at = punctuation_matches[-1].end()
            else:
                split_at = window.rfind(" ", 0, max_chars + 1)

                if split_at <= 0:
                    split_at = max_chars

            chunk = remaining[:split_at].strip()

            if chunk:
                chunks.append(chunk)

            remaining = remaining[split_at:].strip()

        if remaining:
            chunks.append(remaining)

        return chunks


    def process(
        self, 
        text: str,
        voice: str,
        max_chars: int = 150
    ):

        try:
            voice_embedding = self.voice_inpt.get(voice=voice)
        except Exception:
            raise KeyError("the selected voice is not supported by Kokoro TTS model.")
        
        chunks = self._split_text(
            text=text, max_chars=max_chars
        )

        for chunk in chunks:

            source_text = chunk
            chunk = self._phonemize(text=chunk)

            tokens = self._tokenize(chunk, vocab=self.vocab)

            yield KokoroInput(
                tokens = np.array([[0, *tokens, 0]], dtype=np.int64),
                style = np.array(voice_embedding[len(tokens)], dtype=np.float32),
                speed = np.array([1.3], dtype=np.float32),
                text = source_text,
            )
