#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Tuple,
    Age,
    Filesize,
)


def min_age_levels():
    return Tuple(
        title=_("Minimal age of a file"),
        elements=[
            Age(title=_("Warning if younger than")),
            Age(title=_("Critical if younger than")),
        ],
    )


def max_age_levels():
    return Tuple(
        title=_("Maximal age of a file"),
        elements=[
            Age(title=_("Warning if older than")),
            Age(title=_("Critical if older than")),
        ],
    )


def min_size_levels():
    return Tuple(
        title=_("Minimal size of a file"),
        elements=[
            Filesize(title=_("Warning if below")),
            Filesize(title=_("Critical if below")),
        ],
    )


def max_size_levels():
    return Tuple(
        title=_("Maximal size of a file"),
        elements=[
            Filesize(title=_("Warning if above")),
            Filesize(title=_("Critical if above")),
        ],
    )
