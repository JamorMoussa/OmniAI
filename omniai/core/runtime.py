from fastapi import Request

from .manifest import ManifestStore
from .factory import ModelFactory
from .base import OmniAIBaseModel

class ModelRuntimeManager:

    def __init__(
        self, 
    ):
        self.store = ManifestStore()
        self.factory = ModelFactory()

        self.loaded = {}

    def get(
        self, model_id: str
    ) -> OmniAIBaseModel:
        
        existing = self.loaded.get(model_id)

        if existing is not None:
            return existing

        manifest = self.store.get(
            name=model_id
        )

        model = self.factory.create(
            manifest=manifest
        )

        self.loaded[model_id] = model 

        return model

    def close(self):
        for name, model in self.loaded:
            model.close()

            del self.loaded[name]

def get_runtime(request: Request) -> ModelRuntimeManager:
    return request.app.state.runtime

    