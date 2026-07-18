import onnxruntime as ort
from pathlib import Path 
import numpy as np

class ONNXBackend:

    def __init__(
        self,
        session: ort.InferenceSession | None = None 
    ):
        self.session = session 

    @staticmethod
    def load(
        model_path: str | Path 
    ):
        session = (
            ort.InferenceSession(
                path_or_bytes=model_path,
                providers=[
                    "CPUExecutionProvider",
                ],
            )
        )

        return ONNXBackend(
            session=session
        )

    def close(self):
        self.session = None 

    def run(
        self, 
        inputs: dict[str, np.ndarray]
    ):
        return self.session.run(None, inputs)[0]