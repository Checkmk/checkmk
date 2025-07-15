#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.ccc.site import SiteId
from cmk.gui import sites


def execute_command(name: str, args: list[str] | None = None, site: SiteId | None = None) -> None:
    if args:
        formated_args = ";" + ";".join(args)
    else:
        formated_args = ""

    query = "[%d] EC_%s%s" % (int(time.time()), name, formated_args)
    sites.live().command(query, site)
