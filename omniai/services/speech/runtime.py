from omnitts.base import AutoTTSModel
from factory import TTSModelFactory
from store import ManifestStore

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request


class ModelRuntimeManager:

    def __init__(self):

        self.store = ManifestStore()
        self.factory = TTSModelFactory()
        
        self._loaded: dict[str, AutoTTSModel] = {}

    def get(self, name: str) -> AutoTTSModel:

        loaded_model = self._loaded.get(name)

        if loaded_model is not None:
            return loaded_model

        manifest = self.store.get(name=name)

        model = self.factory.create(
            manifest=manifest,
        )

        self._loaded[name] = model
        return model


@asynccontextmanager
async def lifespan(app: FastAPI):

    runtime = ModelRuntimeManager()

    app.state.runtime = runtime

    try:
        yield
    finally:
        runtime.close()


def get_runtime(request: Request) -> ModelRuntimeManager:
    return request.app.state.runtime
