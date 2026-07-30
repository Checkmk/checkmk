#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass
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


@dataclass(frozen=True, kw_only=True)
class ServerInfo:
    url: str
    status: str


@dataclass(frozen=True, kw_only=True)
class FileInfo:
    path: str
    exists: bool
    mode: str | None


@dataclass(frozen=True, kw_only=True)
class StashInfo:
    path: str
    exists: bool
    mode: str | None
    count: int
    next_id: int | None


@dataclass(frozen=True, kw_only=True)
class Problem:
    item: str
    problem: str
    fix: str = ""


@dataclass(frozen=True, kw_only=True)
class Status:
    server: ServerInfo
    secret: FileInfo
    reserved_ids: StashInfo
    legacy_stash: StashInfo
    problems: Sequence[Problem]


def _mode(path: Path) -> str | None:
    try:
        return f"{path.stat().st_mode & 0o777:04o}"
    except OSError:
        return None


def _is_readable_by_others(mode: str | None) -> bool:
    return mode is not None and bool(int(mode, 8) & 0o077)


def _file_info(path: Path) -> FileInfo:
    return FileInfo(path=str(path), exists=path.exists(), mode=_mode(path))


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
        path=str(path),
        exists=path.exists(),
        mode=_mode(path),
        count=len(reserved),
        next_id=reserved[0].id if reserved else None,
    )


def _problems(
    paths: Paths,
    server_url: str,
    server_status: ServerStatus | None,
    reserved: Sequence[WerkId],
    werk_exists: Callable[[WerkId], bool],
) -> Iterator[Problem]:
    # Only a legacy file next to the current ones is a problem: on its own it is the stash
    # that is still in use, and 'werk init' migrates the IDs in it.
    if paths.legacy_stash_file.exists() and (
        paths.secret_file.exists() or paths.stash_file.exists()
    ):
        yield Problem(
            item="legacy_stash",
            problem="exists next to the current werk ID files",
            fix="werk init",
        )

    if not paths.secret_file.exists():
        yield Problem(item="secret", problem="missing", fix="werk init")
    elif _is_readable_by_others(secret_mode := _mode(paths.secret_file)):
        yield Problem(
            item="secret",
            problem=f"readable by others ({secret_mode})",
            fix=f"chmod 600 {paths.secret_file}",
        )

    match server_status:
        case ServerStatus.UNAUTHORIZED:
            yield Problem(item="server", problem="rejected your secret", fix="werk init")
        case ServerStatus.ERROR:
            yield Problem(
                item="server", problem="answered with an error", fix=f"check {server_url}"
            )
        case _:
            pass

    if not reserved and server_status is not ServerStatus.OK:
        yield Problem(
            item="reserved_ids",
            problem="none reserved and the server is unavailable",
            fix="reconnect to the VPN, then 'werk new'",
        )

    for werk_id in reserved:
        if werk_exists(werk_id):
            yield Problem(
                item="reserved_ids",
                problem=f"werk {werk_id} already exists on disk",
                fix=f"remove {werk_id} from the stash",
            )


def collect_status(
    *,
    paths: Paths,
    server_url: str,
    server_status: ServerStatus | None,
    werk_exists: Callable[[WerkId], bool],
) -> Status:
    stash_ids = _stash_ids(paths)
    legacy_ids = _legacy_stash_ids(paths)
    # Without a secret the legacy file is the stash the tool still reserves from, so that
    # is the one whose IDs are available.
    reserved = stash_ids if paths.secret_file.exists() else legacy_ids
    return Status(
        server=ServerInfo(
            url=server_url,
            status=SERVER_NOT_CHECKED if server_status is None else server_status.value,
        ),
        secret=_file_info(paths.secret_file),
        reserved_ids=_stash_info(paths.stash_file, stash_ids),
        legacy_stash=_stash_info(paths.legacy_stash_file, legacy_ids),
        problems=list(_problems(paths, server_url, server_status, reserved, werk_exists)),
    )


def render_json(status: Status) -> str:
    # Every section is emitted unconditionally, including the one the tables hide, so
    # consumers get a fixed shape and never have to probe for keys.
    return json.dumps({"schema_version": SCHEMA_VERSION} | asdict(status), indent=2)


_SERVER_NOTES = {
    SERVER_NOT_CHECKED: "not checked, no secret",
    ServerStatus.OK.value: "reachable, secret accepted",
    ServerStatus.UNAUTHORIZED.value: "reachable, secret rejected",
    ServerStatus.UNREACHABLE.value: "unreachable",
    ServerStatus.ERROR.value: "reachable, but answered with an error",
}

_ITEM_LABELS = {
    "server": "server",
    "secret": "secret",
    "reserved_ids": "reserved ids",
    "legacy_stash": "legacy stash",
}


def _marker(state: bool) -> str:
    return "[green]✓[/]" if state else "[red]✗[/]"


def _reserved_summary(stash: StashInfo) -> str:
    if stash.next_id is None:
        return "no IDs reserved"
    return f"{stash.count} reserved, next {WerkId(stash.next_id)}"


def _table(title: str, *columns: str) -> Table:
    table = Table(box=SIMPLE_HEAD, title=title, title_justify="left", title_style="bold")
    table.add_column("")
    for column in columns:
        table.add_column(column, overflow="fold")
    return table


def _werk_ids_table(status: Status) -> Table:
    table = _table("WERK IDS", "ITEM", "DETAIL", "LOCATION", "MODE")
    table.add_row(
        _marker(status.server.status == ServerStatus.OK.value),
        _ITEM_LABELS["server"],
        _SERVER_NOTES[status.server.status],
        status.server.url,
        "",
    )
    table.add_row(
        _marker(status.secret.exists),
        _ITEM_LABELS["secret"],
        "",
        status.secret.path,
        status.secret.mode or "",
    )
    table.add_row(
        _marker(status.reserved_ids.exists),
        _ITEM_LABELS["reserved_ids"],
        _reserved_summary(status.reserved_ids),
        status.reserved_ids.path,
        status.reserved_ids.mode or "",
    )
    # Shown only while it is there, with the same columns as the stash file so the two can
    # be compared: it either still holds the IDs in use, or it clashes with the new files.
    if status.legacy_stash.exists:
        table.add_row(
            _marker(not status.secret.exists),
            _ITEM_LABELS["legacy_stash"],
            _reserved_summary(status.legacy_stash),
            status.legacy_stash.path,
            status.legacy_stash.mode or "",
        )
    return table


def _problems_table(status: Status) -> Table:
    table = _table("PROBLEMS", "ITEM", "PROBLEM", "FIX")
    for problem in status.problems:
        table.add_row("✗", _ITEM_LABELS[problem.item], problem.problem, problem.fix)
    return table


def render_status(status: Status, console: Console) -> None:
    console.print(_werk_ids_table(status))
    if status.problems:
        console.print(_problems_table(status))
        return
    console.print("[bold]PROBLEMS[/]")
    console.print("[green]✓[/] none found")
