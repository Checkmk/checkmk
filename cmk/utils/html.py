#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

_OK_MARKER = '<b class="stmark state0">OK</b>'
_WARN_MARKER = '<b class="stmark state1">WARN</b>'
_CRIT_MARKER = '<b class="stmark state2">CRIT</b>'
_UNKNOWN_MARKER = '<b class="stmark state3">UNKN</b>'


def replace_state_markers(output: str) -> str:
    return (
        output.replace("(!)", _WARN_MARKER)
        .replace("(!!)", _CRIT_MARKER)
        .replace("(?)", _UNKNOWN_MARKER)
        .replace("(.)", _OK_MARKER)
    )


def get_html_state_marker(state: int) -> str:
    return [_OK_MARKER, _WARN_MARKER, _CRIT_MARKER, _UNKNOWN_MARKER][state]
