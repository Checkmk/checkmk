#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Name the Setup folder a host is configured in, the way Setup names it.

Livestatus has no folder column. A host's folder is only implied by ``filename``, the config file
the host is defined in: Setup writes one ``hosts.mk`` per folder below ``/wato``, so the path
between those two fixed parts is the folder::

    /wato/hosts.mk                ->  ""               the root folder
    /wato/dc_muc/rack1/hosts.mk   ->  "dc_muc/rack1"
    anything else                 ->  None             no Setup folder

That path is not what a user reads, though. Setup shows a folder by its title, which need not
resemble the path at all - "Data center Munich" may well live in ``dc_muc`` - and only Setup knows
it. So the titles are injected (see `SetupFolders`): the column asks for the title of one folder,
the filter asks for all of them, to find the folders a value names.

Two kinds of host have no folder to show, and therefore cannot be filtered by one:

* hosts not managed via Setup, added straight to the monitoring core;
* hosts a remote site owns, whose folders the local Setup does not know.

A third kind has a folder, but not one that says anything about it. The hosts the Dynamic host
configuration creates - Kubernetes objects and piggyback hosts in general - are ordinary Setup
hosts, yet every one of them lands in the single folder its creation rule names, Main by default
and the cluster host's folder for the Kubernetes Quick Setup, so their own nesting never becomes
folder nesting. A Kubernetes topology lives in the host name and in the ``cmk/kubernetes/*``
labels instead; a folder column cannot show it, and labels are the dimension that can.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True, kw_only=True)
class SetupFolders:
    """What this domain needs from Setup: how its folders are titled.

    Two questions rather than one mapping, because they do not cost the same: the title of one
    folder is a lookup, while every title means walking the whole folder tree - which the column,
    redrawn on a timer, has no business doing. They arrive as functions, so Setup answers them off
    its own request-scoped caches and this domain holds nothing of Setup's to call them on.
    """

    title_of: Callable[[str], str | None]
    all_titles: Callable[[], Mapping[str, str]]


class MonitorFolders:
    """How the monitoring pages name the folder a host is configured in.

    Setup is injected as a source and asked when a caller wants to know rather than read out at
    wiring time: its folders live for one request only, and one added meanwhile has to be found.
    While no source is wired no folder has a title, which reads as no folder at all.
    """

    def __init__(self) -> None:
        self._setup: SetupFolders | None = None

    def use_setup_source(self, source: SetupFolders) -> None:
        self._setup = source

    def title_of(self, path: str) -> str | None:
        """The title Setup shows for one folder, None when the user has no folder of that path."""
        return None if self._setup is None else self._setup.title_of(path)

    def titles(self) -> Mapping[str, str]:
        """Every folder the user may know of, titled the way the Folder column shows it."""
        return {} if self._setup is None else self._setup.all_titles()


monitor_folders = MonitorFolders()


def folder_path_from_filename(filename: str) -> str | None:
    """The folder a host defined in ``filename`` sits in, None when that file is not Setup's."""
    path = PurePosixPath(filename)
    if path.name != "hosts.mk" or path.parts[:2] != ("/", "wato"):
        return None
    folder = path.relative_to("/wato").parent
    return "" if folder == PurePosixPath(".") else str(folder)


def folder_title(filename: str, title_of: Callable[[str], str | None]) -> str:
    """The folder to show for a host defined in ``filename``, empty when it has none."""
    if (path := folder_path_from_filename(filename)) is None:
        return ""
    return title_of(path) or ""


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
    needle = value.lower()
    return [_filename_of(path) for path, title in sorted(titles.items()) if needle in title.lower()]


def _filename_of(path: str) -> str:
    """The file Setup writes the hosts of the folder at ``path`` into."""
    return f"/wato/{path}/hosts.mk" if path else "/wato/hosts.mk"
