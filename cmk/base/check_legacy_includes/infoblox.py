#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def check_infoblox_statistics(ty, stats):
    texts: dict[str, list[str]] = {}
    perfdata = []
    for what, what_val, what_textfield, what_info in stats:
        texts.setdefault(str(what_textfield), [])
        texts[what_textfield].append("%d %s" % (what_val, what_info))
        perfdata.append((f"{ty}_{what}", what_val))

    infotexts = []
    for what, entries in texts.items():
        infotexts.append("{}: {}".format(what, ", ".join(entries)))

    return 0, " - ".join(infotexts), perfdata
