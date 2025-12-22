#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cmk.ccc import store
from cmk.crypto.hash import HashAlgorithm
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.type_defs import Key, KeyId

type KeypairMap = dict[KeyId, Key]


class KeypairStore:
    def __init__(self, path: Path, attr: str) -> None:
        super().__init__()
        self._path = path
        self._attr = attr

    def load(self) -> KeypairMap:
        if not self._path.exists():
            return {}

        variables: dict[str, dict[str | int, dict[str, Any]]] = {self._attr: {}}
        with self._path.open("rb") as f:
            exec(f.read(), variables, variables)  # nosec B102 # BNS:aee528
        return self.parse(variables[self._attr])

    def save(self, keys: KeypairMap) -> None:
        self._path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        with store.locked(self._path):
            store.save_mk_file(
                self._path, f"{self._attr}.update({pprint.pformat(self._unparse(keys))})"
            )

    @staticmethod
    def parse(raw_keys: Mapping[str | int, dict[str, str | float | bool]]) -> KeypairMap:
        return {KeyId(key_id): Key.model_validate(raw_key) for key_id, raw_key in raw_keys.items()}

    @staticmethod
    def _unparse(keys: KeypairMap) -> dict[str, dict[str, str | float | bool]]:
        return {key_id: key.model_dump() for key_id, key in keys.items()}

    def choices(self) -> list[tuple[str, str]]:
        choices = []
        for key in self.load().values():
            choices.append((key.fingerprint(HashAlgorithm.MD5), key.alias))
        return sorted(choices, key=lambda x: x[1])

    def get_key_by_digest(self, digest: str) -> tuple[KeyId, Key]:
        for key_id, key in self.load().items():
            if key.fingerprint(HashAlgorithm.MD5) == digest:
                return key_id, key
        raise KeyError()

    def add(self, key: Key) -> None:
        keys = self.load()

        this_digest = key.fingerprint(HashAlgorithm.MD5)
        for key_id, stored_key in keys.items():
            if stored_key.fingerprint(HashAlgorithm.MD5) == this_digest:
                raise MKUserError(
                    None,
                    _("The key / certificate already exists (key: %d, description: %s)")
                    % (key_id, stored_key.alias),
                )

        keys[KeyId.generate()] = key
        self.save(keys)
