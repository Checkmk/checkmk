#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from ._migrations import migrate_to_internal_proxy
from ._preconfigured import InternalProxy, InternalProxySchema

__all__ = [
    "InternalProxy",
    "InternalProxySchema",
    "migrate_to_internal_proxy",
]
