from abc import ABC, abstractmethod


class Provider(ABC):
    NAME = "provider"

    @staticmethod
    @abstractmethod
    def post_save(backup_file: str):
        return

    @staticmethod
    @abstractmethod
    def clean():
        return
