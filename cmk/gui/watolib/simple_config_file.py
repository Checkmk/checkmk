#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from pathlib import Path
from typing import Generic, Mapping, TypeVar

import cmk.utils.store as store

_T = TypeVar("_T")


class WatoSimpleConfigFile(abc.ABC, Generic[_T]):
    """Manage simple .mk config file containing a single dict variable

    The file handling logic is inherited from cmk.utils.store.load_from_mk_file()
    and cmk.utils.store.save_to_mk_file().
    """

    def __init__(self, config_file_path: Path, config_variable: str) -> None:
        self._config_file_path = config_file_path
        self._config_variable = config_variable

    def load_for_reading(self) -> dict[str, _T]:
        return self._load_file(lock=False)

    def load_for_modification(self) -> dict[str, _T]:
        return self._load_file(lock=True)

    def _load_file(self, lock: bool = False) -> dict[str, _T]:
        return store.load_from_mk_file(
            "%s" % self._config_file_path,
            key=self._config_variable,
            default={},
            lock=lock,
        )

    def save(self, cfg: Mapping[str, _T]) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(str(self._config_file_path), self._config_variable, cfg)

    def filter_usable_entries(self, entries: dict[str, _T]) -> dict[str, _T]:
        return entries

    def filter_editable_entries(self, entries: dict[str, _T]) -> dict[str, _T]:
        return entries
