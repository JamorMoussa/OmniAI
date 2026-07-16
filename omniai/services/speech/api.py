from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from omnitts import KokoroTTS, Manifest
    

class SpeechRequest(BaseModel):
    model: str 
    input: str 
    voice: str
    # speed: int

tts = FastAPI()

router = APIRouter(prefix="/v1/audio")
tts.include_router(router=router)

speech_model = KokoroTTS.load(manifest=Manifest.load("/models/kokoro"))


@router.post("/speech")
async def speech(
    request: SpeechRequest
):  
    audio_streams = speech_model.create_stream(
        text= request.input, voice=request.voice
    )

    return StreamingResponse(
        content= map(lambda stream: stream.as_bytes(), audio_streams),
        media_type="audio/wav",
    )

@router.get("/voices")
def voices(
    request: Request
):
    return {
        "voices": speech_model.voices()
    }