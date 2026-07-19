import struct

from fastapi.responses import Response, StreamingResponse
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from omniai.core import ModelRuntimeManager, get_runtime
    

class SpeechRequest(BaseModel):
    model: str 
    input: str 
    voice: str
    # speed: int


speech_router = APIRouter()


def frame_audio_chunks(audio_streams):
    for chunk in audio_streams:
        wav = chunk.as_bytes()
        text = chunk.text.encode("utf-8")
        payload = struct.pack(">I", len(text)) + text + wav
        yield struct.pack(">I", len(payload)) + payload

@speech_router.post("/speech")
async def speech(
    request: SpeechRequest, runtime: ModelRuntimeManager = Depends(get_runtime)
):  

    speech_model = runtime.get(model_id=request.model)

    audio = await run_in_threadpool(
        speech_model.create,
        text=request.input,
        voice=request.voice,
    )

    return Response(
        content=audio.as_bytes(),
        media_type="audio/wav",
    )


@speech_router.post("/speech/stream")
def speech_stream(
    request: SpeechRequest, runtime: ModelRuntimeManager = Depends(get_runtime)
):
    speech_model = runtime.get(model_id=request.model)

    return StreamingResponse(
        content=frame_audio_chunks(
            speech_model.create_stream(text=request.input, voice=request.voice)
        ),
        media_type="application/vnd.omniai.audio-chunks",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Content-Type-Options": "nosniff",
            "X-OmniAI-Stream-Format": "uint32-frame-length,uint32-text-length,utf8-text,wav",
        },
    )

@speech_router.get("/voices")
def voices(
    model: str, runtime: ModelRuntimeManager = Depends(get_runtime)
):
    speech_model = runtime.get(model_id=model)

    return {
        "voices": speech_model.voices()
    }
