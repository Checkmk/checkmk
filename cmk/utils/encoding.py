#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides some bytes-unicode encoding functions"""

from typing import AnyStr

from six import ensure_str


def ensure_str_with_fallback(value: AnyStr, *, encoding: str, fallback: str) -> str:
    try:
        return ensure_str(value, encoding)  # pylint: disable= six-ensure-str-bin-call
    except UnicodeDecodeError:
        return ensure_str(value, fallback)  # pylint: disable= six-ensure-str-bin-call
