#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from pathlib import Path
from typing import Generic, TypeVar

import cmk.utils.store as store

_G = TypeVar("_G")
_T = TypeVar("_T")


class WatoConfigFile(abc.ABC, Generic[_G]):
    """Manage simple .mk config file

    The file handling logic is inherited from cmk.utils.store.load_from_mk_file()
    and cmk.utils.store.save_to_mk_file().
    """

    def __init__(self, config_file_path: Path, config_variable: str) -> None:
        self._config_file_path = config_file_path
        self._config_variable = config_variable

    def load_for_reading(self) -> _G:
        return self._load_file(lock=False)

    def load_for_modification(self) -> _G:
        return self._load_file(lock=True)

    def _load_file(self, lock: bool) -> _G:
        return store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default={},
            lock=lock,
        )

    def save(self, cfg: _G) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(str(self._config_file_path), self._config_variable, cfg)


class WatoSingleConfigFile(WatoConfigFile[_T], Generic[_T]):
    """Manage simple .mk config file containing a single dict variable which represents
    the overall configuration. The 1st level dict represents the configuration
    {base_url: ..., credentials: ...}
    """


class WatoSimpleConfigFile(WatoConfigFile[dict[str, _T]], Generic[_T]):
    """Manage simple .mk config file containing a single dict variable
    with nested entries. The 1st level dict encompasses those entries where each entry
    has its own configuration.

    An example is {"password_1": {...}, "password_2": {...}}
    """

    def filter_usable_entries(self, entries: dict[str, _T]) -> dict[str, _T]:
        return entries

    def filter_editable_entries(self, entries: dict[str, _T]) -> dict[str, _T]:
        return entries
