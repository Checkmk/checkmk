#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Sized
from typing import Generic, TypeVar

from cmk.fetchers import Fetcher
from cmk.fetchers.filecache import FileCache, FileCacheOptions

from cmk.checkengine.fetcher import SourceInfo

_TRawData = TypeVar("_TRawData", bound=Sized)


class Source(Generic[_TRawData], abc.ABC):
    """Abstract source factory.

    Note:
        Pass arguments to `__init__` if they depend on the type of the source;
        pass arguments to the factory method if they are independent.

    See Also:
        https://refactoring.guru/design-patterns/abstract-factory

    """

    @abc.abstractmethod
    def source_info(self) -> SourceInfo: ...

    @abc.abstractmethod
    def fetcher(self) -> Fetcher[_TRawData]: ...

    @abc.abstractmethod
    def file_cache(
        self, *, simulation: bool, file_cache_options: FileCacheOptions
    ) -> FileCache[_TRawData]: ...
