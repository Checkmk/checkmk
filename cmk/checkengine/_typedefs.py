#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import pprint
from collections.abc import Iterator

from cmk.utils.check_utils import ParametersTypeAlias

__all__ = ["Parameters"]


class Parameters(ParametersTypeAlias):
    """Parameter objects are used to pass parameters to plugin functions"""

    def __init__(self, data: ParametersTypeAlias) -> None:
        self._data = dict(data)

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __repr__(self) -> str:
        # use pformat to be testable.
        return f"{self.__class__.__name__}({pprint.pformat(self._data)})"
