from abc import ABC, abstractmethod


class BaseReader(ABC):

    @abstractmethod
    def read(self, source):
        pass