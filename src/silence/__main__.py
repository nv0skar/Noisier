# Silence
# Copyright (C) 2025 Oscar Alvarez Gonzalez

from silence.config import Config, _load_default_config, _load_config

from typing import Any

import sys


class LazyGlobals:
    __slots__ = ("debug", "_config")

    debug: bool
    _config: Config

    def __init__(self):
        self._config = _load_default_config()
        self.debug = False

    def __getattribute__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            pass
        return object.__getattribute__(self._config, name)

    def toggle_debug(self):
        if self.debug:
            print("Cannot toggle off debug at runtime!")
            sys.exit(1)
        self.debug = True

    def load_config(self):
        if self._config != _load_default_config():
            print("Cannot set configuration at runtime!")
            sys.exit(1)
        self._config = _load_config()

    def get(self):
        return self._config


CONFIG: LazyGlobals = LazyGlobals()
