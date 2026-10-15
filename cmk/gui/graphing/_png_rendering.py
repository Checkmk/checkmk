#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

from ._graph_display_config import GraphDisplayConfigImage
from ._graph_png import PngTexts
from ._graph_png_size import PngOptions


def png_options(config: GraphDisplayConfigImage) -> PngOptions:
    return PngOptions(
        size=config.size,
        font_size=config.font_size,
        show_title=config.show_title,
        show_legend=config.show_legend,
        show_vertical_axis=config.show_vertical_axis,
        show_time_axis=config.show_time_axis,
        show_graph_time=config.show_graph_time,
    )


def png_texts() -> PngTexts:
    return PngTexts(
        minimum=_("Min"),
        maximum=_("Max"),
        average=_("Average"),
        last=_("Last"),
        # xgettext: no-python-format
        # astrein: disable=localization-named-placeholder
        date_format=_("%Y-%m-%d"),
        caption=_("for %(date_range)s, resolution: %(resolution)s"),
    )
