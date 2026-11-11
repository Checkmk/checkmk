#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Where Setup writes the hosts of a folder, read back from the file Livestatus reports.

Setup writes the hosts of each folder into ``hosts.mk`` below ``/wato``, and Livestatus reports
that file as a host's ``filename``, not the folder. Setup and the monitoring pages both turn one
into the other, so the layout is read here, below both of them.
"""

__all__ = ["folder_path_from_filename"]


def folder_path_from_filename(filename: str) -> str | None:
    """The folder a host defined in ``filename`` sits in, None when that file is not Setup's.

    Called per row of views that may list thousands of hosts or services, and by their folder
    sorters several times per comparison, so it slices the string Setup wrote rather than parse
    it as a path.
    """
    if filename.startswith("/wato/") and filename.endswith("/hosts.mk"):
        # The prefix and the suffix share the slash of "/wato/hosts.mk", which leaves "".
        return filename[6:-9]
    return None
