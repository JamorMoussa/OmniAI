import struct
import unittest

from omniai.audio.speech.api import frame_audio_chunks


class StubAudioChunk:
    text = "Hello, world!"

    def as_bytes(self):
        return b"RIFF-wave-data"


class SpeechStreamFrameTests(unittest.TestCase):
    def test_frame_contains_text_and_audio(self):
        framed = b"".join(frame_audio_chunks([StubAudioChunk()]))

        frame_length = struct.unpack(">I", framed[:4])[0]
        payload = framed[4:]
        text_length = struct.unpack(">I", payload[:4])[0]
        text_end = 4 + text_length

        self.assertEqual(frame_length, len(payload))
        self.assertEqual(payload[4:text_end].decode("utf-8"), "Hello, world!")
        self.assertEqual(payload[text_end:], b"RIFF-wave-data")
