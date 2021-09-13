#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ipaddress import IPv6Address
from typing import Sequence, Union


def clean_v4_address(chunks: Sequence[Union[int, str]]) -> str:
    return "%d.%d.%d.%d" % tuple(int(i) for i in chunks)


def clean_v6_address(chunks: Sequence[Union[int, str]]) -> str:
    """
    >>> clean_v6_address([32,1,7,40,0,0,80,0,0,0,0,0,0,0,14,249])
    '[2001:728:0:5000::ef9]'
    >>> clean_v6_address([32,1,7,40,0,0,0,0,255,255,0,0,0,0,14,249])
    '[2001:728::ffff:0:0:ef9]'
    """
    ichunks = iter("%02x" % int(i) for i in chunks)
    raw_address = ":".join("%s%s" % pair for pair in zip(ichunks, ichunks))

    return f"[{str(IPv6Address(raw_address))}]"
