from fastapi import FastAPI, APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from runtime import ModelRuntimeManager, get_runtime, lifespan
    

class SpeechRequest(BaseModel):
    model: str 
    input: str 
    voice: str
    # speed: int

speech_app = FastAPI(lifespan=lifespan)

router = APIRouter(prefix="/v1/audio")
speech_app.include_router(router=router)


@router.post("/speech")
async def speech(
    request: SpeechRequest, runtime: ModelRuntimeManager = Depends(get_runtime)
):  

    speech_model = runtime.get(name=request.model)

    audio_streams = speech_model.create_stream(
        text= request.input, voice=request.voice
    )

    return StreamingResponse(
        content= map(lambda stream: stream.as_bytes(), audio_streams),
        media_type="audio/wav",
    )

@router.get("/voices")
def voices(
    model: str, runtime: ModelRuntimeManager = Depends(get_runtime)
):
    speech_model = runtime.get(name=model)

    return {
        "voices": speech_model.voices()
    }