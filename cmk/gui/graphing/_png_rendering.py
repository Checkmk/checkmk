#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

from ._graph_png import PngTexts


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
