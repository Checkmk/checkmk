#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path
from typing import Final

from cmk.utils.store import ObjectStore

UpdateActionState = MutableMapping[str, str]

_UpdateStatePayload = MutableMapping[str, UpdateActionState]


class _UpdateStateSerializer:
    @staticmethod
    def _assert_str(raw: str) -> str:
        if not isinstance(raw, str):
            raise TypeError(raw)
        return raw

    def serialize(self, data: _UpdateStatePayload) -> bytes:
        # Make sure we write it in a strucure s.t. it can be deserialized.
        # Rather crash upon serializing.
        return json.dumps(
            {
                self._assert_str(action_name): {
                    self._assert_str(k): self._assert_str(v) for k, v in action_value.items()
                }
                for action_name, action_value in data.items()
            }
        ).encode()

    @staticmethod
    def deserialize(raw: bytes) -> _UpdateStatePayload:
        return {
            str(action_name): {str(k): str(v) for k, v in raw_action_value.items()}
            for action_name, raw_action_value in json.loads(raw.decode()).items()
        }


class UpdateState:
    _BASE_NAME = "update_state.json"

    def __init__(
        self, store: ObjectStore[_UpdateStatePayload], payload: _UpdateStatePayload
    ) -> None:
        self.store: Final = store
        self.payload: Final = payload

    @classmethod
    def load(cls, path: Path) -> UpdateState:
        store = ObjectStore(path / cls._BASE_NAME, serializer=_UpdateStateSerializer())
        return cls(store, store.read_obj(default={}))

    def save(self) -> None:
        self.store.write_obj(self.payload)

    def setdefault(self, name: str) -> UpdateActionState:
        return self.payload.setdefault(name, {})


def format_warning(msg: str) -> str:
    return f"\033[93m {msg}\033[00m"
