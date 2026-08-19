#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Translate between the Livestatus ``filename`` column and the folder shown to the user.

Livestatus has no folder column. A host's Setup folder is only implied by ``filename``, the
config file the host is defined in: Setup writes one ``hosts.mk`` per folder below ``/wato``, so
the folder is the path between those two fixed parts::

    /wato/hosts.mk              ->  "/"             the root folder
    /wato/network/dc1/hosts.mk  ->  "/network/dc1"
    anything else               ->  ""              not managed via Setup

Reading a folder and filtering by one have to agree on that mapping, so both directions live
here: `folder_from_filename` produces what the user sees, `folder_contains_filters` matches
against exactly that.

A folder carries a second name, the title Setup shows for it, and it need not resemble its path:
"Data center Munich" may well live in ``dc_muc``. Livestatus knows nothing about it, so matching
a title means resolving it to the folders that bear it before asking Livestatus about their
files. `MonitorFolders` is where those titles come from.

Two accepted imprecisions of the filter side, neither reachable with filenames as the monitoring
core emits them: the fixed path parts are matched case-insensitively, and a filename with a
trailing slash is read as a folder but matched as none.
"""

from collections.abc import Callable, Sequence
from pathlib import PurePosixPath
from typing import Protocol

from cmk.ccc.regex import escape_regex_chars
from cmk.gui.logged_in import LoggedInUser

# A folder's path as it appears in a filename, and the title path Setup shows for it.
type TitledFolder = tuple[str, str]


class SetupFolders(Protocol):
    """What this domain needs from Setup: which folders there are, and how they are titled.

    Described as a protocol so Setup's folder tree can be injected without this module importing
    it, and spelled the way Setup spells it, so the tree satisfies this without an adapter on the
    Setup side.
    """

    def folder_choices_fulltitle(self, acting_user: LoggedInUser) -> Sequence[TitledFolder]: ...


class MonitorFolders:
    """The Setup folders the monitoring pages may name, by path and by title.

    Setup is injected as a source and read when a caller asks rather than copied at wiring time:
    its folder tree lives for one request only, and a folder added meanwhile has to be found.
    While no source is wired the titles stay unknown, which leaves filtering by path.
    """

    def __init__(self) -> None:
        self._setup: Callable[[], SetupFolders] | None = None

    def use_setup_source(self, source: Callable[[], SetupFolders]) -> None:
        self._setup = source

    def visible_to(self, user: LoggedInUser) -> Sequence[TitledFolder]:
        """Every folder this user may see, empty while no source is wired.

        Which folders that are is Setup's own answer, gated by its read permissions.
        """
        if self._setup is None:
            return ()
        return self._setup().folder_choices_fulltitle(user)


monitor_folders = MonitorFolders()


def folder_from_filename(filename: str) -> str:
    """The folder to show for a host defined in ``filename``."""
    path = PurePosixPath(filename)
    if path.name != "hosts.mk" or path.parts[:2] != ("/", "wato"):
        # Not managed via Setup, e.g. added directly to the monitoring core.
        return ""
    folder = path.relative_to("/wato").parent
    return "/" if folder == PurePosixPath(".") else f"/{folder}"


def folder_contains_filters(value: str, *, folders: Sequence[TitledFolder] = ()) -> list[str]:
    r"""Livestatus filter lines matching the hosts whose folder carries ``value``.

    A folder is matched when the value is part of the path shown in the Folder column, or part
    of the title Setup shows for it, so a user may type whichever of the two names they know.
    The title is matched here rather than in Livestatus, which never sees one.

        >>> for line in folder_contains_filters("network"):
        ...     print(line)
        Filter: filename ~~ ^/wato/.*network.*/hosts\.mk$

        >>> for line in folder_contains_filters("Munich", folders=[("dc_muc", "Munich")]):
        ...     print(line)
        Filter: filename ~~ ^/wato/.*Munich.*/hosts\.mk$
        Filter: filename = /wato/dc_muc/hosts.mk
        Or: 2

    The value is a literal substring, not a pattern, hence the escaping below.
    """
    # One element per entry on Livestatus' filter stack, each spelled as one or more lines.
    fragments = _path_fragments(value) + _title_fragments(value, folders)

    lines = [line for fragment in fragments for line in fragment]
    if len(fragments) > 1:
        lines.append(f"Or: {len(fragments)}")
    return lines


def _path_fragments(value: str) -> list[list[str]]:
    r"""Matches on the folder path, spelled as a match on the middle of ``filename``.

    Since ``filename`` is ``/wato`` + the folder + ``/hosts.mk``, the pattern is pinned in place
    by the two fixed parts. Anchoring matters: an unpinned match would let ``wato`` or
    ``hosts.mk`` match every host. Two cases the pinned match cannot express follow it.
    """
    pattern = escape_regex_chars(value)

    fragments = [
        # ``value`` inside the folder, past its leading slash.
        [rf"Filter: filename ~~ ^/wato/.*{pattern}.*/hosts\.mk$"],
    ]
    if value.startswith("/"):
        # ``value`` covering the folder's leading slash, i.e. matching a path prefix. The
        # alternative above cannot see that slash, it is part of the fixed ``/wato/``.
        fragments.append([rf"Filter: filename ~~ ^/wato{pattern}.*/hosts\.mk$"])
    if value in ("", "/"):
        # The root folder shows as "/" although its filename holds no folder part at all.
        fragments.append([_matching(_filename_of(""))])
    if not value:
        # Hosts not managed via Setup show no folder at all, which only "" is contained in.
        fragments.append([r"Filter: filename ~~ ^/wato/(.*/)?hosts\.mk$", "Negate:"])
    return fragments


def _title_fragments(value: str, folders: Sequence[TitledFolder]) -> list[list[str]]:
    """One file per folder whose Setup title carries the value.

    A folder the value already matches by path needs no line of its own. That also keeps a value
    every path carries, "/" or the empty one, from repeating every folder there is.
    """
    needle = value.lower()
    fragments: list[list[str]] = []
    for path, title_path in folders:
        if needle not in title_path.lower():
            continue
        filename = _filename_of(path)
        if needle in folder_from_filename(filename).lower():
            continue
        fragments.append([_matching(filename)])
    return fragments


def _filename_of(path: str) -> str:
    """The file Setup writes the hosts of the folder at ``path`` into."""
    return f"/wato/{path}/hosts.mk" if path else "/wato/hosts.mk"


def _matching(filename: str) -> str:
    return f"Filter: filename = {filename}"
