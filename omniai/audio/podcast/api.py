import base64
import io

import httpx
import numpy as np
import soundfile as sf
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator


class PodcastTurn(BaseModel):
    speaker: str
    text: str = Field(min_length=1)
    pause_after_ms: int | None = Field(
        default=None,
        ge=0,
        le=5000,
    )


class PodcastRequest(BaseModel):
    model: str
    speakers: dict[str, str]
    turns: list[PodcastTurn] = Field(min_length=1)
    pause_ms: int = Field(default=350, ge=0, le=5000)
    trim_silence: bool = True

    @model_validator(mode="after")
    def validate_speakers(self):
        unknown_speakers = {
            turn.speaker
            for turn in self.turns
            if turn.speaker not in self.speakers
        }

        if unknown_speakers:
            raise ValueError(
                f"Undefined speakers: {sorted(unknown_speakers)}"
            )

        return self


class PodcastSegment(BaseModel):
    speaker: str
    voice: str
    text: str
    start: float
    end: float
    duration: float


class PodcastSpeaker(BaseModel):
    speaker: str
    voice: str
    duration: float


class PodcastResponse(BaseModel):
    audio: str
    audio_format: str
    sample_rate: int
    duration: float
    speakers: list[PodcastSpeaker]
    segments: list[PodcastSegment]


def trim_outer_silence(
    audio: np.ndarray,
    sample_rate: int,
    padding_ms: int = 20,
) -> np.ndarray:
    """Remove generated leading/trailing silence, retaining a short margin."""
    if not len(audio):
        return audio

    peak = float(np.max(np.abs(audio)))
    if peak == 0:
        return audio

    threshold = max(peak * 0.002, 1e-4)
    audible = np.flatnonzero(np.abs(audio) > threshold)
    if not len(audible):
        return audio

    padding = int(sample_rate * padding_ms / 1000)
    start = max(0, int(audible[0]) - padding)
    end = min(len(audio), int(audible[-1]) + padding + 1)
    return audio[start:end]


async def generate_speech(
    client: httpx.AsyncClient,
    speech_url: str,
    model: str,
    text: str,
    voice: str,
) -> tuple[np.ndarray, int]:
    response = await client.post(
        speech_url,
        json={
            "model": model,
            "input": text,
            "voice": voice,
        },
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=(
                f"Speech generation failed: "
                f"{response.text}"
            ),
        )

    try:
        audio, sample_rate = sf.read(
            io.BytesIO(response.content),
            dtype="float32",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The speech endpoint returned invalid WAV audio.",
        ) from exc

    # Convert stereo to mono when necessary.
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    return audio, sample_rate



podcast_router = APIRouter()


@podcast_router.post("/podcast", response_model=PodcastResponse)
async def create_podcast(
    podcast_request: PodcastRequest,
    request: Request,
):
    speech_url = str(
        request.url_for("speech")
    )

    audio_parts: list[np.ndarray] = []
    podcast_sample_rate: int | None = None
    segments: list[PodcastSegment] = []
    speaker_durations = {
        speaker: 0.0 for speaker in podcast_request.speakers
    }
    elapsed_samples = 0

    async with httpx.AsyncClient(timeout=120.0) as client:
        for index, turn in enumerate(podcast_request.turns):
            voice = podcast_request.speakers[turn.speaker]

            audio, sample_rate = await generate_speech(
                client=client,
                speech_url=speech_url,
                model=podcast_request.model,
                text=turn.text,
                voice=voice,
            )

            if podcast_sample_rate is None:
                podcast_sample_rate = sample_rate

            if sample_rate != podcast_sample_rate:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "All generated audio segments must have "
                        "the same sample rate."
                    ),
                )

            if podcast_request.trim_silence:
                audio = trim_outer_silence(audio, sample_rate)

            audio_parts.append(audio)

            segment_samples = len(audio)
            start = elapsed_samples / podcast_sample_rate
            elapsed_samples += segment_samples
            end = elapsed_samples / podcast_sample_rate
            duration = segment_samples / podcast_sample_rate

            segments.append(
                PodcastSegment(
                    speaker=turn.speaker,
                    voice=voice,
                    text=turn.text,
                    start=start,
                    end=end,
                    duration=duration,
                )
            )
            speaker_durations[turn.speaker] += duration

            # Do not add silence after the final turn.
            if index < len(podcast_request.turns) - 1:
                pause_ms = (
                    turn.pause_after_ms
                    if turn.pause_after_ms is not None
                    else podcast_request.pause_ms
                )

                silence = np.zeros(
                    int(podcast_sample_rate * pause_ms / 1000),
                    dtype=np.float32,
                )

                audio_parts.append(silence)
                elapsed_samples += len(silence)

    if not audio_parts or podcast_sample_rate is None:
        raise HTTPException(
            status_code=400,
            detail="No audio was generated.",
        )

    podcast_audio = np.concatenate(audio_parts)

    # Prevent clipping.
    podcast_audio = np.clip(
        podcast_audio,
        -1.0,
        1.0,
    )

    output_buffer = io.BytesIO()

    sf.write(
        output_buffer,
        podcast_audio,
        podcast_sample_rate,
        format="WAV",
        subtype="PCM_16",
    )

    return PodcastResponse(
        audio=base64.b64encode(output_buffer.getvalue()).decode("ascii"),
        audio_format="wav",
        sample_rate=podcast_sample_rate,
        duration=len(podcast_audio) / podcast_sample_rate,
        speakers=[
            PodcastSpeaker(
                speaker=speaker,
                voice=voice,
                duration=speaker_durations[speaker],
            )
            for speaker, voice in podcast_request.speakers.items()
        ],
        segments=segments,
    )
