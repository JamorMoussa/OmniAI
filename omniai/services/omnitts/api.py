from fastapi import FastAPI, APIRouter, Request

tts = FastAPI()

router = APIRouter(prefix="/v1/audio")
tts.include_router(router=router)


@router.get("/speech")
def speech(
    request: Request
):
    return {
        "message": "hello from omnitts service"
    }


@router.get("/voices")
def voices(
    request: Request
):
    return {
        "message": "voices api"
    }