from fastapi import APIRouter

from .speech.api import speech_router
from .podcast.api import podcast_router

audio_router = APIRouter(prefix="/v1/audio")

audio_router.include_router(speech_router)
audio_router.include_router(podcast_router)




