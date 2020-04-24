#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from types import TracebackType
from typing import Optional, Type

import six

# pylint: disable=cmk-module-layer-violation
from cmk.base.check_utils import RawAgentData
# pylint: enable=cmk-module-layer-violation


class AbstractDataFetcher(six.with_metaclass(abc.ABCMeta, object)):
    """Interface to the data fetchers."""
    @abc.abstractmethod
    def __enter__(self):
        # type: () -> AbstractDataFetcher
        """Prepare the data source."""

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> Optional[bool]
        """Destroy the data source."""

    @abc.abstractmethod
    def data(self):
        # type: () -> RawAgentData
        """Return the data from the source."""
