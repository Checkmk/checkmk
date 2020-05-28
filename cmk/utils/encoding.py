#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides some bytes-unicode encoding functions"""

from typing import AnyStr, Optional

from six import ensure_str


def convert_to_unicode(
    value,
    *,
    encoding=None,
    std_encoding="utf-8",
    fallback_encoding="latin-1",
):
    # type: (AnyStr, Optional[str], str, str) -> str
    if encoding:
        return ensure_str(value, encoding)
    try:
        return ensure_str(value, std_encoding)
    except UnicodeDecodeError:
        return ensure_str(value, fallback_encoding)
