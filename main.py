from contextlib import asynccontextmanager
from fastapi import FastAPI

from omniai.core import ModelRuntimeManager
from omniai.audio import audio_router

@asynccontextmanager
async def lifespan(app: FastAPI):

    runtime = ModelRuntimeManager()

    app.state.runtime = runtime

    try:
        yield
    finally:
        runtime.close()

app = FastAPI(lifespan=lifespan)

app.include_router(router=audio_router)