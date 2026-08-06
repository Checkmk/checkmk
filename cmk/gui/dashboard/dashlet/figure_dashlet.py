#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import override

from cmk.gui.type_defs import SingleInfos

from ..type_defs import DashletConfig
from .base import Dashlet, RelativeLayoutConstraints, WidgetSize

__all__ = ["ABCFigureDashlet"]


class ABCFigureDashlet[T: DashletConfig](Dashlet[T], abc.ABC):
    """Base class for cmk_figures based graphs
    Only contains the dashlet spec, the data generation is handled in the
    DataGenerator classes, to split visualization and data
    """

    @classmethod
    @override
    def type_name(cls) -> str:
        return "figure_dashlet"

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 95

    @override
    def infos(self) -> SingleInfos:
        return ["host", "service"]

    @classmethod
    @override
    def single_infos(cls) -> SingleInfos:
        return []

    @classmethod
    @override
    def has_context(cls) -> bool:
        return True

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(initial_size=WidgetSize(width=56, height=40))
