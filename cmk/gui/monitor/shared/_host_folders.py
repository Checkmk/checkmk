#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Select hosts by the title of the Setup folder they are configured in.

Livestatus has no folder column: a host's folder is only implied by ``filename``, the ``hosts.mk``
Setup writes per folder below ``/wato``. The titles are Setup's, so they are passed in.
"""

import re
from collections.abc import Iterable, Mapping


def folder_matching_filters(value: str, titles: Mapping[str, str]) -> list[str]:
    """Livestatus filter lines selecting the hosts whose folder title carries ``value``.

    A title is Setup's word, not Livestatus', so which folders carry the value is decided here and
    Livestatus is only asked about their files.

        >>> for line in folder_matching_filters("Munich", {"dc_muc": "Data center Munich"}):
        ...     print(line)
        Filter: filename = /wato/dc_muc/hosts.mk

        >>> for line in folder_matching_filters("Rack", {"dc_muc": "Data center Munich"}):
        ...     print(line)
        Filter: state >= 0
        Negate:
    """
    if not (files := folder_files_matching(value, titles)):
        # No folder carries the value, so no host does. Every host has a state, hence not having
        # one selects none - said as a filter, because saying nothing would select every host.
        return ["Filter: state >= 0", "Negate:"]

    lines = [f"Filter: filename = {file}" for file in files]
    if len(files) > 1:
        lines.append(f"Or: {len(files)}")
    return lines


def folder_files_matching(value: str, titles: Mapping[str, str]) -> list[str]:
    """The files of the folders whose title carries ``value``, in a settled order."""
    return [_filename_of(path) for path in folders_titled(value, titles)]


def folders_titled(value: str, titles: Mapping[str, str]) -> list[str]:
    """The paths of the folders whose title carries ``value``, in a settled order."""
    needle = value.lower()
    return [path for path, title in sorted(titles.items()) if needle in title.lower()]


def folders_below(patterns: Iterable[str], titles: Mapping[str, str]) -> list[str]:
    """The paths of the folders below any of ``patterns``, in a settled order.

    A pattern is a folder path as the global search takes it: matched case-insensitively from the
    start of the path, with ``*`` as a wildcard, and its last part may continue - like the legacy
    quicksearch, which asks Livestatus for ``^/wato/<pattern>[^/]*/``.

        >>> folders_below(["linux"], {"linux": "", "linux/web": "", "linux10": "", "win": ""})
        ['linux', 'linux/web', 'linux10']

        >>> folders_below(["*/web"], {"linux": "", "linux/web": "", "win/web": ""})
        ['linux/web', 'win/web']
    """
    regexes = [
        re.compile(".*".join(re.escape(part) for part in pattern.split("*")) + "[^/]*/", re.I)
        for pattern in patterns
    ]
    return [path for path in sorted(titles) if any(r.match(f"{path}/") for r in regexes)]


def _filename_of(path: str) -> str:
    """The file Setup writes the hosts of the folder at ``path`` into."""
    return f"/wato/{path}/hosts.mk" if path else "/wato/hosts.mk"
