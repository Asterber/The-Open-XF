import json
import os
from pathlib import Path
from typing import Self

from pydantic import BaseModel

from vc_parser.schemas import NodePath

CACHE_DIR = Path('cache')


class FileCache(BaseModel):
    data: dict[NodePath, list[BaseModel]]
    klass: type[BaseModel]

    def get(self, path: NodePath):
        return self.data.get(path, list())

    def set(self, path: NodePath, data: list):
        self.data[path] = data
        self.save()

    def has_key(self, path: NodePath):
        return path in self.data

    @staticmethod
    def get_file_path(klass: type[BaseModel]) -> str:
        return CACHE_DIR / (klass.__name__.lower() + "_cache" + ".json")

    @classmethod
    def load(cls, klass: type[BaseModel]) -> Self:
        data = {}
        name = cls.get_file_path(klass)
        if os.path.exists(name):
            with open(name) as f:
                data = json.load(f)
                for k, v in data.items():
                    data[k] = [klass(**x) for x in v]
        return cls(data=data, klass=klass)

    def save(self):
        with open(self.get_file_path(self.klass), "w") as f:
            to_dump = {}
            for k, v in self.data.items():
                to_dump[k] = [x.model_dump() for x in v]
            json.dump(to_dump, f)


class Cache(BaseModel):
    triggers: FileCache
    trigger_actions: FileCache
    variables: FileCache
    assets: FileCache
    asset_names: FileCache
    view_navigation: FileCache
