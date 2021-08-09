#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# no used space check for Tablsspaces with CONTENTS in ('TEMPORARY','UNDO')
# It is impossible to check the used space in UNDO and TEMPORARY Tablespaces
# These Types of Tablespaces are ignored in this plugin.
# This restriction is only working with newer agents, because we need an
# additional parameter at end if each datafile

from ..agent_based_api.v1 import render


def get_tablespace_levels_in_bytes(size_bytes, params):
    # If the magic factor is used, take table size and magic factor
    # into account in order to move levels
    magic = params.get("magic")

    # Use tablespace size dependent dynamic levels or static levels
    if isinstance(params.get("levels"), tuple):
        warn, crit = params.get("levels")
    else:
        # A list of levels. Choose the correct one depending on the
        # size of the current tablespace
        for to_size, this_levels in params.get("levels"):
            if size_bytes > to_size:
                warn, crit = this_levels
                break
        else:
            return None, None, "", False

    # warn/crit level are float => percentages of max size, otherwise MB
    if isinstance(warn, float):
        output_as_percentage = True
        if magic:
            normsize = params["magic_normsize"] * 1024 * 1024
            hbytes_size = size_bytes / float(normsize)
            felt_size = hbytes_size**magic
            scale = felt_size / hbytes_size
            warn *= scale
            crit *= scale
            max_warning_level, max_critical_level = params["magic_maxlevels"]
            warn = min(warn, max_warning_level)
            crit = min(crit, max_critical_level)
        levels_text = " (warn/crit at %.1f%%/%.1f%%)" % (warn, crit)
        warn_bytes = warn * size_bytes / 100
        crit_bytes = crit * size_bytes / 100

    # Absolute free space in MB
    else:
        output_as_percentage = False
        warn_bytes = warn * 1024 * 1024
        crit_bytes = crit * 1024 * 1024
        levels_text = " (warn/crit at %s/%s)" % (render.bytes(warn_bytes), render.bytes(crit_bytes))

    return warn_bytes, crit_bytes, levels_text, output_as_percentage
