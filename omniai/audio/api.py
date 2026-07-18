from fastapi import APIRouter

from .speech.api import speech_router

audio_router = APIRouter(prefix="/v1/audio")

audio_router.include_router(speech_router)




