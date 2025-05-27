#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# This file is auto-generated via the cmk-shared-typing package.
# Do not edit manually.
#
# fmt: off


from __future__ import annotations

from dataclasses import dataclass


@dataclass(kw_only=True)
class ModeHostI18n:
    error_host_not_dns_resolvable: str
    success_host_dns_resolvable: str


@dataclass(kw_only=True)
class ModeHost:
    i18n: ModeHostI18n
