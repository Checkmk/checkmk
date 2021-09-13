#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""User-defined exceptions and error handling related constant."""

import enum
import traceback
from types import TracebackType
from typing import Tuple, Type

__all__ = [
    "MKAgentError",
    "MKBailOut",
    "MKIPAddressLookupError",
    "MKEmptyAgentData",
    "MKException",
    "MKFetcherError",
    "MKGeneralException",
    "MKParseFunctionError",
    "MKSkipCheck",
    "MKSNMPError",
    "MKTerminate",
    "MKTimeout",
    "OnError",
]


# never used directly in the code. Just some wrapper to make all of our
# exceptions handleable with one call
class MKException(Exception):
    pass


class MKFetcherError(MKException):
    """An exception common to the fetchers."""


class MKAgentError(MKFetcherError):
    pass


class MKSNMPError(MKFetcherError):
    pass


class MKEmptyAgentData(MKAgentError):
    pass


class MKParseFunctionError(MKException):
    def __init__(
        self, exception_type: Type[Exception], exception: Exception, backtrace: TracebackType
    ) -> None:
        self.exception_type = exception_type
        self.exception = exception
        self.backtrace = backtrace
        super().__init__(self, exception_type, exception, backtrace)

    def exc_info(self) -> Tuple[Type[Exception], Exception, TracebackType]:
        return self.exception_type, self.exception, self.backtrace

    def __str__(self) -> str:
        return "%r\n%s" % (self.exception, "".join(traceback.format_tb(self.backtrace)))


class MKSkipCheck(MKException):
    pass


class MKGeneralException(MKException):
    pass


# This exception is raises when the current program execution should be
# terminated. For example it is raised by the SIGINT signal handler to
# propagate the termination up the callstack.
# This should be raised in all cases where the program termination is a
# "normal" case and no exception handling like printing a stack trace
# nor an error message should be done. The program is stopped with
# exit code 0.
class MKTerminate(MKException):
    pass


# This is raised to print an error message and then end the program.
# The program should catch this at top level and end exit the program
# with exit code 3, in order to be compatible with monitoring plugin API.
class MKBailOut(MKException):
    pass


class MKTimeout(MKException):
    """Raise when a timeout is reached.

    Note:
        It is used during keepalive mode. It is also used by the
        automations which have a timeout set.

    See also:
        `cmk.utils.timeout` has a context manager using it.
    """


class MKIPAddressLookupError(MKGeneralException):
    pass


class OnError(enum.Enum):
    RAISE = "raise"
    WARN = "warn"
    IGNORE = "ignore"
