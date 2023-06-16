#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Container

from cmk.utils.validatedstr import ValidatedString

__all__ = ["SectionName"]


class SectionName(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        return super().exceptions()
