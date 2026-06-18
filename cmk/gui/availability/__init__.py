#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Availability computation, options and layout for host/service/BI availability.

The public API surface of this package is defined by ``__all__`` below. These are
the only symbols that external consumers (reporting and SLA in
``cmk.gui.nonfree.pro``) are allowed to rely on. Everything else lives in the
submodules and may be refactored freely; import it directly from the submodule that
defines it (e.g. ``from cmk.gui.availability.type_defs import AVMode``).
"""

from .annotations import (
    get_annotation_date_render_function,
    get_relevant_annotations,
    load_annotations,
)
from .bi import get_bi_availability
from .computation import compute_availability, compute_availability_groups, object_title
from .layout import layout_availability_table, layout_timeline
from .options import (
    get_av_computation_options,
    get_av_display_options,
    get_availability_options_from_request,
    get_default_avoptions,
)
from .rawdata import get_availability_rawdata
from .type_defs import (
    AVData,
    AVEntry,
    AVLayoutTable,
    AVLayoutTimeline,
    AVObjectType,
    AVOptions,
    AVRawData,
    AVSpan,
    SiteHost,
)

# Public API surface -- the symbols external consumers (reporting, SLA) may import.
# See the module docstring before adding to this list.
__all__ = [
    "AVData",
    "AVEntry",
    "AVLayoutTable",
    "AVLayoutTimeline",
    "AVObjectType",
    "AVOptions",
    "AVRawData",
    "AVSpan",
    "SiteHost",
    "compute_availability",
    "compute_availability_groups",
    "get_annotation_date_render_function",
    "get_av_computation_options",
    "get_av_display_options",
    "get_availability_options_from_request",
    "get_availability_rawdata",
    "get_bi_availability",
    "get_default_avoptions",
    "get_relevant_annotations",
    "layout_availability_table",
    "layout_timeline",
    "load_annotations",
    "object_title",
]
