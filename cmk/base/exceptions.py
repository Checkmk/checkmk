#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from types import TracebackType  # pylint: disable=unused-import
from typing import Tuple, Type  # pylint: disable=unused-import

from cmk.utils.exceptions import (
    MKException,
    MKGeneralException,
)


class MKAgentError(MKException):
    pass


class MKIPAddressLookupError(MKGeneralException):
    pass


class MKEmptyAgentData(MKAgentError):
    pass


class MKParseFunctionError(MKException):
    def __init__(self, exception_type, exception, backtrace):
        # type: (Type[Exception], Exception, TracebackType) -> None
        self.exception_type = exception_type
        self.exception = exception
        self.backtrace = backtrace
        super(MKParseFunctionError, self).__init__(self, exception_type, exception, backtrace)

    def exc_info(self):
        # type: () -> Tuple[Type[Exception], Exception, TracebackType]
        return self.exception_type, self.exception, self.backtrace

    def __str__(self):
        # type: () -> str
        return "%r\n%s" % (self.exception, "".join(traceback.format_tb(self.backtrace)))


class MKSNMPError(MKException):
    pass


class MKSkipCheck(MKException):
    pass
