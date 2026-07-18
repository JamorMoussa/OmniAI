from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Self

from .manifest import Manifest


class BaseOutput(ABC):
    ... 

class BaseInput(ABC):
    ... 


class OmniAIBaseModel(ABC):

    @staticmethod
    @abstractmethod
    def load(
        manifest: Manifest, 
    ) -> Self:
        ...


    @abstractmethod
    def create(
        self, 
    ) -> Generator[BaseOutput]:
        ...

    @abstractmethod
    def close(self):
        ... 


class OmniAIBaseProcessor(ABC):

    @staticmethod
    @abstractmethod
    def load(
        manifest: Manifest, 
    ) -> Self:
        ...


    @abstractmethod
    def process(
        self, 
    ) -> Generator[BaseInput]:
        ...