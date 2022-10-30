from abc import ABC, abstractmethod


class Provider(ABC):
    NAME = "provider"

    @abstractmethod
    @staticmethod
    def post_save(backup_file: str):
        return

    @abstractmethod
    @staticmethod
    def clean():
        return
