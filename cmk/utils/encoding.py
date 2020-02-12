#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides some bytes-unicode encoding functions"""

from typing import (  # pylint: disable=unused-import
    AnyStr, Text, Optional,
)
import six


def convert_to_unicode(
    value,
    encoding=None,
    std_encoding="utf-8",
    fallback_encoding="latin-1",
    on_error=None,
):
    # type: (AnyStr, Optional[str], str, str, Optional[Text]) -> Text
    if isinstance(value, six.text_type):
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


def ensure_unicode(value):
    # type: (AnyStr) -> Text
    if isinstance(value, six.text_type):
        return value
    return value.decode("utf-8")


def ensure_bytestr(value):
    # type: (AnyStr) -> bytes
    if isinstance(value, six.binary_type):
        return value
    return value.encode("utf-8")


def make_utf8(value):
    # type: (AnyStr) -> bytes
    if isinstance(value, six.text_type):
        return value.encode('utf-8')
    return value
