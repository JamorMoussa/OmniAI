from omnitts import Manifest, KokoroTTS

from pathlib import Path
import json
import os 


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
            with open(dir / "config.json", "r", encoding="utf-8") as f:
                config = json.load(f)

            manifests[config["model"]] = Manifest.load(manifest_path=dir)

        return manifests

    def list(self) -> list[Manifest]:
        return list(self.manifests.items())

