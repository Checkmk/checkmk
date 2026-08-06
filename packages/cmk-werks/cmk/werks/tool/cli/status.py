#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from rich.box import SIMPLE_HEAD
from rich.console import Console
from rich.table import Table

from .id_pool import load_legacy_stash_from_file, Paths, ServerStatus
from .stash import Stash
from .werk import WerkId

SERVER_NOT_CHECKED = "not_checked"

# Bump whenever the JSON document changes shape, so consumers can branch on it.
SCHEMA_VERSION = 1


class Item(StrEnum):
    SERVER = "server"
    SECRET = "secret"
    RESERVED_IDS = "reserved_ids"
    LEGACY_STASH = "legacy_stash"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class SetupState(StrEnum):
    # Which of the secret, the stash file and the legacy stash file exist decides which
    # stash the tool reserves from. Every combination that is not the current setup gets
    # its own state, so each one can be reported with the fix that actually applies.
    SERVER = "server"
    LEGACY = "legacy"
    ORPHANED_LEGACY = "orphaned_legacy"
    ORPHANED_STASH = "orphaned_stash"
    CONFLICT = "conflict"
    UNINITIALIZED = "uninitialized"


@dataclass(frozen=True, kw_only=True)
class SetupInfo:
    state: SetupState
    active_stash: Item | None


@dataclass(frozen=True, kw_only=True)
class ServerInfo:
    url: str
    status: str


@dataclass(frozen=True, kw_only=True)
class FileInfo:
    path: Path
    exists: bool
    mode: str | None


@dataclass(frozen=True, kw_only=True)
class StashInfo:
    path: Path
    exists: bool
    mode: str | None
    count: int
    next_id: int | None


@dataclass(frozen=True, kw_only=True)
class Problem:
    item: Item
    severity: Severity
    problem: str
    fix: str = ""


@dataclass(frozen=True, kw_only=True)
class Status:
    setup: SetupInfo
    server: ServerInfo
    secret: FileInfo
    reserved_ids: StashInfo
    legacy_stash: StashInfo
    problems: Sequence[Problem]

    @property
    def has_errors(self) -> bool:
        return any(problem.severity is Severity.ERROR for problem in self.problems)


def _mode(path: Path) -> str | None:
    try:
        return f"{path.stat().st_mode & 0o777:04o}"
    except OSError:
        return None


def _is_readable_by_others(mode: str | None) -> bool:
    return mode is not None and bool(int(mode, 8) & 0o077)


def _replace_home(home: Path, path: Path) -> Path:
    # The output is meant to be pasted into tickets and chats, so the name of the home
    # directory is replaced on the way out. Rich styles the parts of a path separately, so
    # this has to happen before rendering, not on the rendered output.
    try:
        return Path("$HOME") / path.relative_to(home)
    except ValueError:
        return path


def _file_info(path: Path) -> FileInfo:
    return FileInfo(path=path, exists=path.exists(), mode=_mode(path))


def _sorted_ids(raw_ids: Iterable[int]) -> Sequence[WerkId]:
    return [WerkId(raw_id) for raw_id in sorted(raw_ids)]


def _stash_ids(paths: Paths) -> Sequence[WerkId]:
    # Deliberately not id_pool.load_stash_from_file(): that bails out when both files
    # exist, which is exactly the state `werk status` has to stay able to report.
    if paths.stash_file.exists():
        raw = Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8")).ids
        return _sorted_ids(raw)
    return []


def _legacy_stash_ids(paths: Paths) -> Sequence[WerkId]:
    if not paths.legacy_stash_file.exists():
        return []
    by_project = load_legacy_stash_from_file(paths).ids_by_project
    return _sorted_ids(raw_id for ids in by_project.values() for raw_id in ids)


def _stash_info(path: Path, reserved: Sequence[WerkId]) -> StashInfo:
    return StashInfo(
        path=path,
        exists=path.exists(),
        mode=_mode(path),
        count=len(reserved),
        next_id=reserved[0].id if reserved else None,
    )


def _setup_state(paths: Paths) -> SetupState:
    secret = paths.secret_file.exists()
    stash = paths.stash_file.exists()
    legacy = paths.legacy_stash_file.exists()
    if stash and legacy:
        return SetupState.CONFLICT
    if legacy:
        return SetupState.ORPHANED_LEGACY if secret else SetupState.LEGACY
    if secret:
        return SetupState.SERVER
    return SetupState.ORPHANED_STASH if stash else SetupState.UNINITIALIZED


def _active_stash(state: SetupState) -> Item | None:
    # The stash the tool reserves from, mirroring Paths.active_stash_file. None means that
    # no stash is in use: either there is none, or the tool cannot tell which one counts.
    match state:
        case SetupState.SERVER | SetupState.ORPHANED_LEGACY:
            return Item.RESERVED_IDS
        case SetupState.LEGACY:
            return Item.LEGACY_STASH
        case _:
            return None


# Exactly one problem per state, attached to the file it is about. The state decides which
# files are expected to be there, so nothing else looks at their existence.
_SETUP_PROBLEMS: Mapping[SetupState, Problem | None] = {
    SetupState.SERVER: None,
    # Nothing is broken in the legacy state: it is the setup from before the werk ID
    # server, and 'werk new' keeps working as long as the file holds IDs.
    SetupState.LEGACY: Problem(
        item=Item.LEGACY_STASH,
        severity=Severity.WARNING,
        problem="still the stash in use, the werk ID server is not set up yet",
        fix="werk init",
    ),
    SetupState.ORPHANED_LEGACY: Problem(
        item=Item.LEGACY_STASH,
        severity=Severity.WARNING,
        problem="left over next to the secret, its IDs are not used any more",
        fix="merge the IDs you still need into the stash by hand, then delete it",
    ),
    SetupState.ORPHANED_STASH: Problem(
        item=Item.SECRET,
        severity=Severity.ERROR,
        problem="missing, so the reserved IDs are not used",
        fix="werk init",
    ),
    SetupState.CONFLICT: Problem(
        item=Item.LEGACY_STASH,
        severity=Severity.ERROR,
        problem="exists next to the current stash file, every other command bails out",
        # Deliberately not 'werk init': it needs the ID server, so it is no help in the
        # state that made every other command bail out, and it carries over only the IDs
        # of project 'cmk' before deleting the file, losing all the others.
        fix="look at both stash files and merge them by hand",
    ),
    SetupState.UNINITIALIZED: Problem(
        item=Item.SECRET,
        severity=Severity.ERROR,
        problem="missing, no werk IDs are set up",
        fix="werk init",
    ),
}


def _setup_problems(state: SetupState) -> Iterator[Problem]:
    if (problem := _SETUP_PROBLEMS[state]) is not None:
        yield problem


def _secret_problems(home: Path, paths: Paths) -> Iterator[Problem]:
    if not paths.secret_file.exists():
        return
    if _is_readable_by_others(mode := _mode(paths.secret_file)):
        yield Problem(
            item=Item.SECRET,
            severity=Severity.ERROR,
            problem=f"readable by others ({mode})",
            fix=f"chmod 600 {_replace_home(home, paths.secret_file)}",
        )


def _server_problems(server_url: str, server_status: ServerStatus | None) -> Iterator[Problem]:
    match server_status:
        case ServerStatus.UNAUTHORIZED:
            yield Problem(
                item=Item.SERVER,
                severity=Severity.ERROR,
                problem="rejected your secret",
                fix="werk init",
            )
        case ServerStatus.ERROR:
            yield Problem(
                item=Item.SERVER,
                severity=Severity.ERROR,
                problem="answered with an error",
                fix=f"check {server_url}",
            )
        case _:
            pass


def _reserved_id_problems(
    active_stash: Item,
    reserved: Sequence[WerkId],
    server_status: ServerStatus | None,
    werk_exists: Callable[[WerkId], bool],
) -> Iterator[Problem]:
    if not reserved and server_status is not ServerStatus.OK:
        yield Problem(
            item=active_stash,
            severity=Severity.ERROR,
            problem="none reserved and the server is unavailable",
            fix="reconnect to the VPN, then 'werk new'",
        )

    for werk_id in reserved:
        if werk_exists(werk_id):
            yield Problem(
                item=active_stash,
                severity=Severity.ERROR,
                problem=f"werk {werk_id} already exists on disk",
                fix=f"remove {werk_id} from the stash",
            )


def collect_status(
    *,
    home: Path,
    paths: Paths,
    server_url: str,
    server_status: ServerStatus | None,
    werk_exists: Callable[[WerkId], bool],
) -> Status:
    state = _setup_state(paths)
    active_stash = _active_stash(state)
    stash_ids = _stash_ids(paths)
    legacy_ids = _legacy_stash_ids(paths)
    match active_stash:
        case Item.RESERVED_IDS:
            reserved = stash_ids
        case Item.LEGACY_STASH:
            reserved = legacy_ids
        case _:
            reserved = []
    return Status(
        setup=SetupInfo(state=state, active_stash=active_stash),
        server=ServerInfo(
            url=server_url,
            status=SERVER_NOT_CHECKED if server_status is None else server_status.value,
        ),
        secret=_file_info(paths.secret_file),
        reserved_ids=_stash_info(paths.stash_file, stash_ids),
        legacy_stash=_stash_info(paths.legacy_stash_file, legacy_ids),
        problems=[
            # The state decides which files are expected to be there, so the existence of
            # each one is reported here and nowhere else.
            *_setup_problems(state),
            *_secret_problems(home, paths),
            *_server_problems(server_url, server_status),
            # Without a stash in use there are no IDs to judge, and the state above already
            # says why.
            *(
                _reserved_id_problems(active_stash, reserved, server_status, werk_exists)
                if active_stash is not None
                else ()
            ),
        ],
    )


def render_json(home: Path, status: Status) -> str:
    # Every section is emitted unconditionally, including the one the tables hide, so
    # consumers get a fixed shape and never have to probe for keys.
    # Only the paths need `default`: the enums are strings already.
    return json.dumps(
        {"schema_version": SCHEMA_VERSION} | asdict(status),
        indent=2,
        default=lambda path: str(_replace_home(home, path)),
    )


_SETUP_NOTES = {
    SetupState.SERVER: "the werk ID server hands out IDs",
    SetupState.LEGACY: "not migrated yet, IDs come from the legacy stash",
    SetupState.ORPHANED_LEGACY: "migrated, but a legacy stash is left over",
    SetupState.ORPHANED_STASH: "IDs are reserved, but the secret they belong to is gone",
    SetupState.CONFLICT: "two stash files, the tool cannot tell which one counts",
    SetupState.UNINITIALIZED: "nothing is set up yet",
}

_SERVER_NOTES = {
    SERVER_NOT_CHECKED: "not checked, no secret",
    ServerStatus.OK.value: "reachable, secret accepted",
    ServerStatus.UNAUTHORIZED.value: "reachable, secret rejected",
    ServerStatus.UNREACHABLE.value: "unreachable",
    ServerStatus.ERROR.value: "reachable, but answered with an error",
}

_ITEM_LABELS = {
    Item.SERVER: "server",
    Item.SECRET: "secret",
    Item.RESERVED_IDS: "reserved ids",
    Item.LEGACY_STASH: "legacy stash",
}

_SEVERITY_MARKERS = {
    Severity.ERROR: "[red]✗[/]",
    Severity.WARNING: "[yellow]![/]",
}


_OK_MARKER = "[green]✓[/]"

# A file that is not there and is not a problem either: nothing to report, but a ✓ would
# read as "it is there".
_ABSENT_MARKER = "[dim]-[/]"


def _severity_marker(severities: Iterable[Severity]) -> str | None:
    collected = set(severities)
    if Severity.ERROR in collected:
        return _SEVERITY_MARKERS[Severity.ERROR]
    if Severity.WARNING in collected:
        return _SEVERITY_MARKERS[Severity.WARNING]
    return None


def _item_marker(status: Status, item: Item, *, exists: bool = True) -> str:
    severities = (problem.severity for problem in status.problems if problem.item == item)
    return _severity_marker(severities) or (_OK_MARKER if exists else _ABSENT_MARKER)


def _state_marker(state: SetupState) -> str:
    # Only the state itself, so this row does not turn red for a problem that is about the
    # server or a single reserved ID.
    problem = _SETUP_PROBLEMS[state]
    return _OK_MARKER if problem is None else _SEVERITY_MARKERS[problem.severity]


def _reserved_summary(stash: StashInfo) -> str:
    if stash.next_id is None:
        return "no IDs reserved"
    return f"{stash.count} reserved, next {WerkId(stash.next_id)}"


def _stash_detail(status: Status, stash: StashInfo, item: Item) -> str:
    in_use = "in use" if status.setup.active_stash is item else "not in use"
    return f"{_reserved_summary(stash)} ({in_use})"


def _table(title: str, *columns: str) -> Table:
    table = Table(box=SIMPLE_HEAD, title=title, title_justify="left", title_style="bold")
    table.add_column("")
    for column in columns:
        table.add_column(column, overflow="fold")
    return table


def _werk_ids_table(home: Path, status: Status) -> Table:
    table = _table("WERK IDS", "ITEM", "DETAIL", "LOCATION", "MODE")
    # The state is the row that explains the others: which files are expected to be there,
    # and which stash the IDs come from.
    table.add_row(
        _state_marker(status.setup.state),
        "setup",
        _SETUP_NOTES[status.setup.state],
        "",
        "",
    )
    table.add_row(
        _item_marker(status, Item.SERVER),
        _ITEM_LABELS[Item.SERVER],
        _SERVER_NOTES[status.server.status],
        status.server.url,
        "",
    )
    table.add_row(
        _item_marker(status, Item.SECRET, exists=status.secret.exists),
        _ITEM_LABELS[Item.SECRET],
        "",
        str(_replace_home(home, status.secret.path)),
        status.secret.mode or "",
    )
    table.add_row(
        _item_marker(status, Item.RESERVED_IDS, exists=status.reserved_ids.exists),
        _ITEM_LABELS[Item.RESERVED_IDS],
        _stash_detail(status, status.reserved_ids, Item.RESERVED_IDS),
        str(_replace_home(home, status.reserved_ids.path)),
        status.reserved_ids.mode or "",
    )
    # Shown only while it is there, with the same columns as the stash file so the two can
    # be compared: it either still holds the IDs in use, or it clashes with the new files.
    if status.legacy_stash.exists:
        table.add_row(
            _item_marker(status, Item.LEGACY_STASH),
            _ITEM_LABELS[Item.LEGACY_STASH],
            _stash_detail(status, status.legacy_stash, Item.LEGACY_STASH),
            str(_replace_home(home, status.legacy_stash.path)),
            status.legacy_stash.mode or "",
        )
    return table


def _problems_table(status: Status) -> Table:
    table = _table("PROBLEMS", "ITEM", "PROBLEM", "FIX")
    for problem in status.problems:
        table.add_row(
            _SEVERITY_MARKERS[problem.severity],
            _ITEM_LABELS[problem.item],
            problem.problem,
            problem.fix,
        )
    return table


def render_status(home: Path, status: Status, console: Console) -> None:
    console.print(_werk_ids_table(home, status))
    if status.problems:
        console.print(_problems_table(status))
        return
    console.print("[bold]PROBLEMS[/]")
    console.print("[green]✓[/] none found")
