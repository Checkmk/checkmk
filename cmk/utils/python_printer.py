#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Print (a subset of) Python values independent of the Python version."""

import sys
from typing import IO, Optional  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from io import StringIO as StrIO
else:
    from io import BytesIO as StrIO


def pprint(obj, stream=None):
    PythonPrinter(stream=stream).pprint(obj)


def pformat(obj):
    return PythonPrinter().pformat(obj)


class PythonPrinter(object):
    def __init__(self, stream=None):
        # type: (Optional[IO[str]]) -> None
        self._stream = sys.stdout if stream is None else stream

    def pprint(self, obj):
        # type: (object) -> None
        self._format(obj, self._stream)
        self._stream.write('\n')

    def pformat(self, obj):
        # type: (object) -> str
        sio = StrIO()
        self._format(obj, sio)
        return sio.getvalue()

    def _format(self, obj, stream):
        # type: (object, IO[str]) -> None
        stream.write(repr(obj))
