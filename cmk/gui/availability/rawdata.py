#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Dispatcher for fetching availability raw data.

This module exists to break the import cycle that would arise if
get_availability_rawdata lived in computation.py:

    bi.py imports spans_by_object from computation.py
    computation.py would need to import get_bi_availability_rawdata from bi.py
    → cycle

By placing the dispatcher here, the import graph is acyclic:
    rawdata.py → bi.py → computation.py
"""

from livestatus import OnlySites

from cmk.gui.type_defs import FilterHeader, ViewProcessTracking, VisualContext

from .bi import get_bi_availability_rawdata
from .computation import get_host_service_availability_rawdata
from .type_defs import AVObjectSpec, AVObjectType, AVOptions, AVRawData


def get_availability_rawdata(
    what: AVObjectType,
    context: VisualContext,
    filterheaders: FilterHeader,
    only_sites: OnlySites,
    av_object: AVObjectSpec,
    include_output: bool,
    include_long_output: bool,
    avoptions: AVOptions,
    view_process_tracking: ViewProcessTracking | None = None,
) -> tuple[AVRawData, bool]:
    if what == "bi":
        return get_bi_availability_rawdata(
            filterheaders, only_sites, av_object, include_output, avoptions
        )
    return get_host_service_availability_rawdata(
        what,
        context,
        filterheaders,
        only_sites,
        av_object,
        include_output,
        include_long_output,
        avoptions,
        view_process_tracking,
    )
