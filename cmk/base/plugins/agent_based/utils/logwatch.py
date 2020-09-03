#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plugin is notorious for being an exception to just about every rule    #
#   or best practice that applies to check plugin development.                          #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

from typing import Dict, List, TypedDict

ItemData = TypedDict(
    "ItemData",
    {
        'attr': str,
        'lines': List[str],
    },
    total=True,
)

SectionLogwatch = TypedDict(
    "SectionLogwatch",
    {
        'errors': List[str],
        'logfiles': Dict[str, ItemData],
    },
    total=True,
)
