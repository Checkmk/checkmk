#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


_OK_MARKER = '<b class="stmarkOK">OK</b>'
_WARN_MARKER = '<b class="stmarkWARNING">WARN</b>'
_CRIT_MARKER = '<b class="stmarkCRITICAL">CRIT</b>'
_UNKNOWN_MARKER = '<b class="stmarkUNKNOWN">UNKN</b>'


def replace_state_markers(output: str) -> str:
    return (
        output.replace("(!)", _WARN_MARKER)
        .replace("(!!)", _CRIT_MARKER)
        .replace("(?)", _UNKNOWN_MARKER)
        .replace("(.)", _OK_MARKER)
    )
