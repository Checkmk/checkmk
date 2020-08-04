#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from types import TracebackType
from typing import Any, Dict, Optional, Type

from cmk.utils.exceptions import MKException
from cmk.utils.type_defs import AgentRawData


class MKFetcherError(MKException):
    """An exception common to the fetchers."""


class AbstractDataFetcher(metaclass=abc.ABCMeta):
    """Interface to the data fetchers."""
    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> 'AbstractDataFetcher':
        """Deserialize from JSON."""
        return cls(**serialized)  # type: ignore[call-arg]

    @abc.abstractmethod
    def __enter__(self) -> 'AbstractDataFetcher':
        """Prepare the data source."""

    @abc.abstractmethod
    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> Optional[bool]:
        """Destroy the data source."""

    @abc.abstractmethod
    def data(self) -> AgentRawData:
        """Return the data from the source."""
