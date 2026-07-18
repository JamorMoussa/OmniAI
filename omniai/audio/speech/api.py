from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from omniai.core import ModelRuntimeManager, get_runtime
    

class SpeechRequest(BaseModel):
    model: str 
    input: str 
    voice: str
    # speed: int


speech_router = APIRouter()

@speech_router.post("/speech")
async def speech(
    request: SpeechRequest, runtime: ModelRuntimeManager = Depends(get_runtime)
):  

    speech_model = runtime.get(model_id=request.model)

    audio_streams = speech_model.create_stream(
        text= request.input, voice=request.voice
    )

    return StreamingResponse(
        content= map(lambda stream: stream.as_bytes(), audio_streams),
        media_type="audio/wav",
    )

@speech_router.get("/voices")
def voices(
    model: str, runtime: ModelRuntimeManager = Depends(get_runtime)
):
    speech_model = runtime.get(model_id=model)

    return {
        "voices": speech_model.voices()
    }