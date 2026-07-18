from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationInfo, 
    field_validator
)
import os 


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Task(StrEnum):
    TEXT_TO_SPEECH = "text-to-speech"


class Artifact(StrictModel):
    path: Path
    sha256: str | None = None

    @field_validator("path", mode="after")
    @classmethod
    def resolve_path(
        cls,
        path: Path,
        info: ValidationInfo,
    ) -> Path:
        # Keep absolute paths unchanged.
        if path.is_absolute():
            return path.resolve()

        context = info.context or {}
        manifest_directory = context.get("manifest_directory")

        if manifest_directory is None:
            raise ValueError(
                "Manifest directory is required to resolve artifact paths"
            )

        base_directory = Path(manifest_directory).resolve()
        resolved_path = (base_directory / path).resolve()

        # Prevent paths such as ../../some-file from escaping the model folder.
        if not resolved_path.is_relative_to(base_directory):
            raise ValueError(
                f"Artifact path escapes model directory: {path}"
            )

        return resolved_path


class ONNXArtifacts(StrictModel):
    model: Artifact
    voices: Artifact | None = None
    vocab: Artifact | None = None


class ONNXBackend(StrictModel):
    type: Literal["onnx"]
    artifacts: ONNXArtifacts


class SpeechDefaults(StrictModel):
    voice: str = "af_heart"
    speed: float = Field(default=1.0, gt=0, le=4)
    response_format: Literal["wav", "pcm", "mp3"] = "wav"
    sample_rate: int = Field(default=24000, gt=0)


class Manifest(StrictModel):
    version: int
    id: str
    name: str
    description: str | None = None
    model_class: str 

    @classmethod
    def load(cls, path: str | Path) -> "Manifest":
        
        manifest_path = Path(path) / "manifest.yaml"

        with manifest_path.open(encoding="utf-8") as file:
            raw = yaml.safe_load(file)

        if not isinstance(raw, dict):
            raise ValueError("Manifest root must be an object")

        return manifest_adapter.validate_python(
            raw,
            context={"manifest_directory": manifest_path.parent},
        )


class SpeechManifest(Manifest):
    task: Literal[Task.TEXT_TO_SPEECH]
    backend: ONNXBackend
    defaults: SpeechDefaults = Field(default_factory=SpeechDefaults)


ManifestVariant = Annotated[
    SpeechManifest,
    Field(discriminator="task"),
]

manifest_adapter = TypeAdapter(ManifestVariant)


class ManifestStore:

    def __init__(
        self
    ):
        path = Path(os.environ.get("OMNIAI_HOME")) 

        if not path.exists():
            raise FileExistsError("the '~/.omniai/models' directory is not exist")

        self.manifests = self._load_manifests(path=path)


    def get(
        self, 
        name: str
    ) -> Manifest:

        return self.manifests.get(name)

    def _load_manifests(
        self, 
        path: Path 
    ) -> dict[str, Manifest]:

        dirs = list(filter(
            lambda d:d.is_dir(), path.rglob('*')
        ))

        manifests = {}

        for dir in dirs:
            manifest = Manifest.load(path=dir)
            manifests[manifest.id] = manifest

        return manifests

    def list(self) -> list[Manifest]:
        return list(self.manifests.items())

