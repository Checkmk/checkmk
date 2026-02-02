#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import abc

from cmk.gui.type_defs import SingleInfos

from .base import Dashlet, RelativeLayoutConstraints, T, WidgetSize

__all__ = ["ABCFigureDashlet"]


class ABCFigureDashlet(Dashlet[T], abc.ABC):
    """Base class for cmk_figures based graphs
    Only contains the dashlet spec, the data generation is handled in the
    DataGenerator classes, to split visualization and data
    """

    @classmethod
    def type_name(cls) -> str:
        return "figure_dashlet"

    @classmethod
    def sort_index(cls) -> int:
        return 95

    def infos(self) -> SingleInfos:
        return ["host", "service"]

    @classmethod
    def single_infos(cls) -> SingleInfos:
        return []

    @classmethod
    def has_context(cls) -> bool:
        return True

    @classmethod
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(initial_size=WidgetSize(width=56, height=40))
