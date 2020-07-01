#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from contextlib import suppress
from typing import Any, IO


# TODO: This should be obsoleted:
#   - either pick a log level
#   - or write to sys.stdout|err
def output(text: str, *args: Any, **kwargs: Any) -> None:
    if args:
        text = text % args
    # TODO: Replace kwargs with keyword only arg in Python 3.
    stream: IO[str] = kwargs.pop("stream", sys.stdout)
    assert not kwargs

    with suppress(IOError):
        # Suppress broken pipe due to, e.g., | head.
        stream.write(text)
        stream.flush()
