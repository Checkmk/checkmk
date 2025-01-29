#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.painter.v0 import PainterRegistry

from ..sorter import SorterRegistry
from .painter import PainterPerfometer
from .sorter import SorterPerfometer


def register(sorter_registry: SorterRegistry, painter_registry: PainterRegistry) -> None:
    sorter_registry.register(SorterPerfometer)
    painter_registry.register(PainterPerfometer)


__all__ = [
    "register",
]
