#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Iterable,
    Union,
)


def render_mac_address(phys_address: Union[Iterable[int], str]) -> str:
    if isinstance(phys_address, str):
        mac_bytes = (ord(x) for x in phys_address)
    else:
        mac_bytes = (x for x in phys_address)
    return (":".join(["%02s" % hex(m)[2:] for m in mac_bytes]).replace(' ', '0')).upper()
