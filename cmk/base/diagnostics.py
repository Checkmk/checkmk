#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.paths import (
    diagnostics_dir,
    omd_root,
)
import cmk.base.console as console


def create_diagnostics_dump():
    # type: () -> None
    console.output("Create diagnostics dump in %s\n" % diagnostics_dir.relative_to(omd_root))
