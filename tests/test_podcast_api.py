import base64
import io
import unittest
from unittest.mock import AsyncMock, patch

import numpy as np
import soundfile as sf

from omniai.audio.podcast.api import (
    PodcastRequest,
    create_podcast,
    trim_outer_silence,
)


class StubRequest:
    def url_for(self, name):
        return "http://test/v1/audio/speech"


class PodcastResponseTests(unittest.IsolatedAsyncioTestCase):
    def test_trims_generated_silence_but_keeps_padding(self):
        audio = np.concatenate(
            (
                np.zeros(12_000, dtype=np.float32),
                np.ones(24_000, dtype=np.float32),
                np.zeros(12_000, dtype=np.float32),
            )
        )

        trimmed = trim_outer_silence(audio, sample_rate=24_000)

        self.assertEqual(len(trimmed), 24_960)
        self.assertEqual(np.count_nonzero(trimmed), 24_000)

    async def test_response_contains_audio_and_segment_timing(self):
        request = PodcastRequest(
            model="kokoro",
            speakers={"host": "af_heart", "guest": "am_adam"},
            turns=[
                {"speaker": "host", "text": "Welcome."},
                {"speaker": "guest", "text": "Thank you."},
            ],
            pause_ms=500,
        )

        generated = AsyncMock(
            side_effect=[
                (np.zeros(24_000, dtype=np.float32), 24_000),
                (np.zeros(12_000, dtype=np.float32), 24_000),
            ]
        )

        with patch("omniai.audio.podcast.api.generate_speech", generated):
            response = await create_podcast(request, StubRequest())

        audio, sample_rate = sf.read(io.BytesIO(base64.b64decode(response.audio)))

        self.assertEqual(sample_rate, 24_000)
        self.assertEqual(len(audio), 48_000)
        self.assertEqual(response.duration, 2.0)
        self.assertEqual(response.segments[0].start, 0.0)
        self.assertEqual(response.segments[0].end, 1.0)
        self.assertEqual(response.segments[1].start, 1.5)
        self.assertEqual(response.segments[1].duration, 0.5)
        self.assertEqual(response.speakers[0].duration, 1.0)
        self.assertEqual(response.speakers[1].duration, 0.5)
