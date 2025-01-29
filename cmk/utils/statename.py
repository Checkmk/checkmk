#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.i18n import _


# TODO: Rename to service_state_names()
def core_state_names() -> dict[int, str]:
    return {
        -1: _("NODATA"),
        0: _("OK"),
        1: _("WARNING"),
        2: _("CRITICAL"),
        3: _("UNKNOWN"),
    }


def service_state_name(state_num: int, deflt: str = "") -> str:
    return core_state_names().get(state_num, deflt)


def short_service_state_names() -> dict[int, str]:
    return {
        -1: _("PEND"),
        0: _("OK"),
        1: _("WARN"),
        2: _("CRIT"),
        3: _("UNKN"),
    }


def short_service_state_name(state_num: int, deflt: str = "") -> str:
    return short_service_state_names().get(state_num, deflt)


def host_state_name(state_num: int, deflt: str = "") -> str:
    states = {
        0: _("UP"),
        1: _("DOWN"),
        2: _("UNREACHABLE"),
    }
    return states.get(state_num, deflt)


def short_host_state_name(state_num: int, deflt: str = "") -> str:
    states = {0: _("UP"), 1: _("DOWN"), 2: _("UNREACH")}
    return states.get(state_num, deflt)
