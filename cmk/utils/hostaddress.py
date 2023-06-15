#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType, TypeAlias

__all__ = ["HostAddress", "HostName"]

HostAddress = NewType("HostAddress", str)
# Let us be honest here, we do not actually make a difference
# between HostAddress and HostName in our code.
HostName: TypeAlias = HostAddress
