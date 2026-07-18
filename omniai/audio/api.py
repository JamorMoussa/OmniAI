from fastapi import APIRouter

from .speech.api import speech_router

audio_rounter = APIRouter(prefix="/v1/audio")

audio_rounter.include_router(speech_router)




