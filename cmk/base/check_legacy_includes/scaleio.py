#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from contextlib import suppress

from cmk.plugins.lib.scaleio import convert_scaleio_space_into_mb


def convert_scaleio_space(unit: str, value: float) -> float | None:
    """Convert the space from the storage pool to MB

    >>> convert_scaleio_space("Not_known", 1.0)

    """

    with suppress(KeyError):
        return convert_scaleio_space_into_mb(unit, value)
    return None
