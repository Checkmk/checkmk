#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides some bytes-unicode encoding functions"""

from typing import AnyStr, Optional


def convert_to_unicode(
    value,
    encoding=None,
    std_encoding="utf-8",
    fallback_encoding="latin-1",
    on_error=None,
):
    # type: (AnyStr, Optional[str], str, str, Optional[str]) -> str
    if isinstance(value, str):
        return value

    if encoding:
        return value.decode(encoding)

    try:
        return value.decode(std_encoding)
    except UnicodeDecodeError:
        pass

    try:
        return value.decode(fallback_encoding)
    except UnicodeDecodeError:
        if on_error is None:
            raise
        return on_error


def ensure_text(value):
    # type: (AnyStr) -> str
    if isinstance(value, str):
        return value
    return value.decode("utf-8")


def ensure_binary(value):
    # type: (AnyStr) -> bytes
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")
