from abc import abstractmethod

from omniai.core.base import OmniAIBaseModel


class SpeechModel(OmniAIBaseModel):

    @abstractmethod
    def voices(self) -> list[str]:
        ...