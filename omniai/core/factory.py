from importlib import import_module

from .base import OmniAIBaseModel
from .manifest import Manifest, Task


class InvalidModelLoaderError(Exception):
    pass


class ModelFactory:

    service_map = {
        Task.TEXT_TO_SPEECH: "omniai.audio.speech"
    }

    def create(
        self,
        manifest: Manifest,
    ) -> OmniAIBaseModel:
        
        loader_class = (
            self._resolve(
                module_name=ModelFactory.get(task=manifest.task),
                model_class=manifest.model_class
            )
        )

        return loader_class.load(
            manifest=manifest
        )

    @classmethod
    def get(
        cls, task: 'Task'
    ):
        if not isinstance(task, Task):
            raise TypeError("task should be instance of 'Task'")

        return cls.service_map[task]

    def _resolve(
        self,
        module_name: str,
        model_class: str,
    ) -> type[OmniAIBaseModel]:

        try:
            module = import_module(name=module_name)
            loader_class = getattr(module, model_class)

        except (ImportError, AttributeError) as error:
            raise InvalidModelLoaderError(
                f"Cannot import model: {module_name}.{model_class}"
            ) from error

        if not isinstance(loader_class, type):
            raise InvalidModelLoaderError(
                f"{module_name}.{model_class} is not a class"
            )

        if not issubclass(loader_class, OmniAIBaseModel):
            raise InvalidModelLoaderError(
                f"{module_name}.{model_class} must inherit from OmniAIBaseModel"
            )

        return loader_class