from importlib import import_module

from omnitts.base import AutoTTSModel
from omnitts import Manifest


class InvalidModelLoaderError(Exception):
    pass


class TTSModelFactory:

    def create(
        self,
        manifest: Manifest,
    ) -> AutoTTSModel:
        
        loader_class = self._resolve(manifest.loader)

        return loader_class.load(
            manifest=manifest
        )

    def _resolve(
        self,
        loader_path: str,
    ) -> type[AutoTTSModel]:
        try:
            module_name, class_name = loader_path.split(":", maxsplit=1)

        except ValueError:

            raise InvalidModelLoaderError(
                f"Invalid loader path: {loader_path!r}. "
                "Expected 'module:ClassName'."
            ) from None

        try:
            module = import_module(name=module_name)
            loader_class = getattr(module, class_name)

        except (ImportError, AttributeError) as error:
            raise InvalidModelLoaderError(
                f"Cannot import model loader: {loader_path}"
            ) from error

        if not isinstance(loader_class, type):
            raise InvalidModelLoaderError(
                f"{loader_path} is not a class"
            )

        if not issubclass(loader_class, AutoTTSModel):
            raise InvalidModelLoaderError(
                f"{loader_path} must inherit from AutoTTSModel"
            )

        return loader_class