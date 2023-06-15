#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container
from typing import Final

__all__ = ["EVERYTHING"]


class _Everything(Container):
    def __contains__(self, __other: object) -> bool:
        return True


EVERYTHING: Final = _Everything()
