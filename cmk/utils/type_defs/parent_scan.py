#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Optional, Tuple

from ._misc import HostAddress, HostName

Gateways = List[
    Tuple[Optional[Tuple[Optional[HostName], HostAddress, Optional[HostName]]], str, int, str]
]
