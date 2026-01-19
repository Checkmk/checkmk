#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Mapping, Sized
from functools import partial
from typing import final, Protocol, Self, TypeVar

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import MKTimeout
from cmk.helper_interface import FetcherError

from ._abstract import Fetcher, Mode
from ._secrets import FetcherSecrets
from .filecache import FileCache

__all__ = [
    "PlainFetcherTrigger",
    "FetcherTrigger",
]

_TRawData = TypeVar("_TRawData", bound=Sized)


class FetcherTrigger(abc.ABC):
    @final
    def get_raw_data(
        self,
        file_cache: FileCache[_TRawData],
        fetcher: Fetcher[_TRawData],
        mode: Mode,
        secrets: FetcherSecrets,
    ) -> result.Result[_TRawData, Exception]:
        try:
            cached = file_cache.read(mode)
            if cached is not None:
                return result.OK(cached)

            if file_cache.simulation:
                raise FetcherError(f"{fetcher}: data unavailable in simulation mode")

            fetched: result.Result[_TRawData, Exception] = result.Error(
                FetcherError("unknown error")
            )
            fetched = self._trigger(fetcher, mode, secrets)
            fetched.map(partial(file_cache.write, mode=mode))
            return fetched

        except MKTimeout:
            raise

        except Exception as exc:
            return result.Error(exc)

    @abc.abstractmethod
    def _trigger(
        self, fetcher: Fetcher[_TRawData], mode: Mode, secrets: FetcherSecrets
    ) -> result.Result[_TRawData, Exception]:
        raise NotImplementedError()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FetcherTrigger):
            return NotImplemented
        return type(self) is type(other) and self.serialized_params() == other.serialized_params()

    @abc.abstractmethod
    def serialized_params(self) -> Mapping[str, str]:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def from_params(cls, params: Mapping[str, str]) -> Self:
        raise NotImplementedError()


class FetcherTriggerFactory(Protocol):
    def __call__(self, relay_id: str | None) -> FetcherTrigger: ...


class PlainFetcherTrigger(FetcherTrigger):
    """A simple trigger that fetches data without any additional logic."""

    def _trigger(
        self, fetcher: Fetcher[_TRawData], mode: Mode, secrets: FetcherSecrets
    ) -> result.Result[_TRawData, Exception]:
        with secrets.provide_file(), fetcher:
            return fetcher.fetch(mode)

    def serialized_params(self) -> Mapping[str, str]:
        """Return an empty mapping as there are no parameters to serialize."""
        return {}

    @classmethod
    def from_params(cls, params: Mapping[str, str]) -> Self:
        """Create a PlainFetcherTrigger from serialized parameters."""
        return cls(**params)
