#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import errno
import json
import logging
import os
import shutil
import tempfile
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Self

from cmk.ccc.hostaddress import HostAddress, HostName

from ._inotify import Event, INotify, Masks
from ._paths import payload_dir, source_status_dir

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class PiggybackMetaData:
    source: HostName
    piggybacked: HostName
    last_update: int
    last_contact: int | None

    def serialize(self) -> str:
        return json.dumps({k: None if v is None else str(v) for k, v in asdict(self).items()})

    @classmethod
    def deserialize(cls, serialized: str, /) -> Self:
        raw = json.loads(serialized)
        return cls(
            source=HostName(raw["source"]),
            piggybacked=HostName(raw["piggybacked"]),
            last_update=int(raw["last_update"]),
            last_contact=None if (i := raw["last_contact"]) is None else int(i),
        )


@dataclass(frozen=True)
class PiggybackMessage:
    meta: PiggybackMetaData
    raw_data: bytes


# ***** Terminology *****
# "piggybacked_host_folder":
# - tmp/check_mk/piggyback/HOST
#
# "piggybacked_hostname":
# - Path(tmp/check_mk/piggyback/HOST).name
#
# "piggybacked_host_source":
# - tmp/check_mk/piggyback/HOST/SOURCE
#
# "source_state_file":
# - tmp/check_mk/piggyback_sources/SOURCE
#
# "source_hostname":
# - Path(tmp/check_mk/piggyback/HOST/SOURCE).name
# - Path(tmp/check_mk/piggyback_sources/SOURCE).name


def watch_new_messages(omd_root: Path) -> Iterator[PiggybackMessage]:
    """Yields piggyback messages as they come in."""

    inotify = INotify()
    watch_for_new_piggybacked_hosts = inotify.add_watch(payload_dir(omd_root), Masks.CREATE)
    watch_for_deleted_status_files = inotify.add_watch(source_status_dir(omd_root), Masks.DELETE)
    for folder in _get_piggybacked_host_folders(omd_root):
        inotify.add_watch(folder, Masks.MOVED_TO)

    for event in inotify.read_forever():
        # check if a new piggybacked host folder was created
        if event.watchee == watch_for_new_piggybacked_hosts:
            if event.type & Masks.CREATE:
                inotify.add_watch(event.watchee.path / event.name, Masks.MOVED_TO)
                # Handle all files already in the folder (we rather have duplicates than missing files)
                yield from get_messages_for(HostAddress(event.name), omd_root)
            continue
        if event.watchee == watch_for_deleted_status_files:
            if event.type & Masks.DELETE:
                source = HostName(event.name)
                for piggybacked_host in _get_piggybacked_hosts_for_source(omd_root, source):
                    yield PiggybackMessage(
                        PiggybackMetaData(
                            source=source,
                            piggybacked=piggybacked_host,
                            last_update=int(time.time()),
                            last_contact=None,
                        ),
                        b"",
                    )
            continue

        if message := _make_message_from_event(event, omd_root):
            yield message


def _make_message_from_event(event: Event, omd_root: Path) -> PiggybackMessage | None:
    source = HostAddress(event.name)
    piggybacked = HostName(event.watchee.path.name)
    status_file_path = _get_source_status_file_path(source, omd_root)
    payload_file_path = event.watchee.path / event.name

    if (mtime := _get_mtime(payload_file_path)) is None:
        return None

    return PiggybackMessage(
        PiggybackMetaData(
            source=source,
            piggybacked=piggybacked,
            last_update=mtime,
            last_contact=_get_mtime(status_file_path),
        ),
        payload_file_path.read_bytes(),
    )


def get_messages_for(
    piggybacked_hostname: HostAddress, omd_root: Path
) -> Sequence[PiggybackMessage]:
    """Returns piggyback messages for the given host"""
    piggyback_meta_data = _get_payload_meta_data(piggybacked_hostname, omd_root)
    logger.debug("%s piggyback files for '%s'.", len(piggyback_meta_data), piggybacked_hostname)

    piggyback_data = []
    for meta_data in piggyback_meta_data:
        content_path = _get_piggybacked_file_path(meta_data.source, meta_data.piggybacked, omd_root)
        try:
            # Raw data is always stored as bytes. Later the content is
            # converted to unicode in abstact.py:_parse_info which respects
            # 'encoding' in section options.
            raw_data = content_path.read_bytes()

        except FileNotFoundError:
            # race condition: file was removed between listing and reading
            continue

        logger.debug("Read piggyback file '%s'", content_path)
        piggyback_data.append(PiggybackMessage(meta_data, raw_data))

    return piggyback_data


def get_piggybacked_host_with_sources(
    omd_root: Path, piggybacked_hostname: HostName | None = None
) -> Mapping[HostAddress, Sequence[PiggybackMetaData]]:
    """Generates all piggyback pig/piggybacked host pairs"""
    return {
        piggybacked_host: _get_payload_meta_data(piggybacked_host, omd_root)
        for piggybacked_host_folder in (
            [d for d in [payload_dir(omd_root) / piggybacked_hostname] if d.exists()]
            if piggybacked_hostname
            else _get_piggybacked_host_folders(omd_root)
        )
        if (piggybacked_host := HostAddress(piggybacked_host_folder.name))
    }


def _get_piggybacked_hosts_for_source(omd_root: Path, source: HostName) -> Sequence[HostName]:
    return [
        HostName(piggybacked_host.name)
        for piggybacked_host in _get_piggybacked_host_folders(omd_root)
        if (piggybacked_host / source).exists()
    ]


def _remove_piggyback_file(piggyback_file_path: Path) -> bool:
    try:
        piggyback_file_path.unlink()
        return True
    except FileNotFoundError:
        return False


def remove_source_status_file(source_hostname: HostName, omd_root: Path) -> bool:
    """Remove the source_status_file of this piggyback host which will
    mark the piggyback data from this source as outdated."""
    source_status_path = _get_source_status_file_path(source_hostname, omd_root)
    return _remove_piggyback_file(source_status_path)


def store_piggyback_raw_data(
    source_hostname: HostName,
    piggybacked_raw_data: Mapping[HostName, Sequence[bytes]],
    message_timestamp: float,
    contact_timestamp: float | None,
    omd_root: Path,
) -> None:
    if contact_timestamp is None:
        # Cleanup the status file when no piggyback data was sent this turn.
        logger.debug("Received no piggyback data")
        remove_source_status_file(source_hostname, omd_root)
        return
    # Store the last contact with this piggyback source to be able to filter outdated data later
    # We use the mtime of this file later for comparison.
    # Only do this for hosts that sent piggyback data this turn.
    logger.debug("Received piggyback data for %d hosts", len(piggybacked_raw_data))
    status_file_path = _get_source_status_file_path(source_hostname, omd_root)
    # usually the status file is updated with the same timestamp as the piggyback files, but in
    # case of distributed piggyback we want to keep the original timestamps so the fetchers etc.
    # work as if on the source system
    _write_file_with_mtime(file_path=status_file_path, content=b"", mtime=contact_timestamp)

    for piggybacked_hostname, lines in piggybacked_raw_data.items():
        logger.debug("Storing piggyback data for: %r", piggybacked_hostname)
        # Raw data is always stored as bytes. Later the content is
        # converted to unicode in abstact.py:_parse_info which respects
        # 'encoding' in section options.
        _write_file_with_mtime(
            file_path=_get_piggybacked_file_path(source_hostname, piggybacked_hostname, omd_root),
            content=b"%s\n" % b"\n".join(lines),
            mtime=message_timestamp,
        )


def _write_file_with_mtime(
    file_path: Path,
    content: bytes,
    mtime: float,
) -> None:
    """Create a file with the given mtime in a race-condition free manner"""
    file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)

    with tempfile.NamedTemporaryFile(
        "wb", dir=str(file_path.parent), prefix=f".{file_path.name}.new", delete=False
    ) as tmp:
        tmp_path = tmp.name
        tmp.write(content)

    tmp_stats = os.stat(tmp_path)
    os.utime(tmp_path, (tmp_stats.st_atime, mtime))
    os.rename(tmp_path, str(file_path))


#   .--folders/files-------------------------------------------------------.
#   |         __       _     _                  ____ _ _                   |
#   |        / _| ___ | | __| | ___ _ __ ___   / / _(_) | ___  ___         |
#   |       | |_ / _ \| |/ _` |/ _ \ '__/ __| / / |_| | |/ _ \/ __|        |
#   |       |  _| (_) | | (_| |  __/ |  \__ \/ /|  _| | |  __/\__ \        |
#   |       |_|  \___/|_|\__,_|\___|_|  |___/_/ |_| |_|_|\___||___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _get_payload_meta_data(
    piggybacked_hostname: HostName, omd_root: Path
) -> Sequence[PiggybackMetaData]:
    """Gather a list of piggyback files to read for further processing.

    Please note that there may be multiple parallel calls executing
    store_piggyback_raw_data() or cleanup_piggyback_files() functions.
    All these functions need to deal with suddenly vanishing or updated files/directories.
    """
    piggybacked_host_folder = payload_dir(omd_root) / Path(piggybacked_hostname)
    meta_data = []
    for payload_file in _files_in(piggybacked_host_folder):
        source = HostAddress(payload_file.name)
        status_file_path = _get_source_status_file_path(source, omd_root)

        if (mtime := _get_mtime(payload_file)) is None:
            continue

        meta_data.append(
            PiggybackMetaData(
                source=source,
                piggybacked=piggybacked_hostname,
                last_update=mtime,
                last_contact=_get_mtime(status_file_path),
            )
        )
    return meta_data


def _get_piggybacked_host_folders(omd_root: Path) -> Sequence[Path]:
    return _files_in(payload_dir(omd_root))


def _get_source_state_files(omd_root: Path) -> Sequence[Path]:
    return _files_in(source_status_dir(omd_root))


def _files_in(path: Path) -> Sequence[Path]:
    """Return a sorted sequence of files in `path` excluding hidden files.

    While the order of the files _should_ not matter, in some weird cases it might.
    We don't expect that to happen (let alone be noticed), but in case it *does* happen, at least be predictable.
    """
    try:
        return sorted(f for f in path.iterdir() if not f.name.startswith("."))
    except FileNotFoundError:
        return []


def _get_source_status_file_path(source_hostname: HostName, omd_root: Path) -> Path:
    return source_status_dir(omd_root) / str(source_hostname)


def _get_piggybacked_file_path(
    source_hostname: HostName,
    piggybacked_hostname: HostName | HostAddress,
    omd_root: Path,
) -> Path:
    return payload_dir(omd_root).joinpath(piggybacked_hostname, source_hostname)


# .
#   .--clean up------------------------------------------------------------.
#   |                     _                                                |
#   |                 ___| | ___  __ _ _ __    _   _ _ __                  |
#   |                / __| |/ _ \/ _` | '_ \  | | | | '_ \                 |
#   |               | (__| |  __/ (_| | | | | | |_| | |_) |                |
#   |                \___|_|\___|\__,_|_| |_|  \__,_| .__/                 |
#   |                                               |_|                    |
#   '----------------------------------------------------------------------'


def cleanup_piggyback_files(cut_off_timestamp: float, omd_root: Path) -> None:
    """This is a housekeeping job to clean up different old files from the
    piggyback directories.

    # Source status files and/or piggybacked data files are cleaned up/deleted
    # if and only if they have exceeded the maximum cache age configured in the
    # global settings or in the rule 'Piggybacked Host Files'."""
    logger.debug(
        "Cleanup piggyback data from before %s (%s).",
        _render_datetime(cut_off_timestamp),
        cut_off_timestamp,
    )

    piggybacked_hosts_settings = [
        (piggybacked_host_folder, _files_in(piggybacked_host_folder))
        for piggybacked_host_folder in _get_piggybacked_host_folders(omd_root)
    ]

    _cleanup_old_source_status_files(_get_source_state_files(omd_root), cut_off_timestamp)
    _cleanup_old_piggybacked_files(piggybacked_hosts_settings, cut_off_timestamp)


def _cleanup_old_source_status_files(
    source_state_files: Sequence[Path],
    cut_off_timestamp: float,
) -> None:
    """Remove source status files which exceed provided maximum age."""
    for source_state_file in source_state_files:
        if (mtime := _get_mtime(source_state_file)) is None:
            continue  # File has been removed, that's OK.

        if mtime < cut_off_timestamp:
            logger.debug(
                "Piggyback source status file '%s' too old (%s). Remove it.",
                source_state_file,
                _render_datetime(mtime),
            )
            _remove_piggyback_file(source_state_file)


def _cleanup_old_piggybacked_files(
    piggybacked_hosts_settings: Iterable[tuple[Path, Iterable[Path]]], cut_off_timestamp: float
) -> None:
    """Remove piggybacked data files which exceed provided maximum age."""

    for piggybacked_host_folder, source_hosts in piggybacked_hosts_settings:
        for piggybacked_host_source in source_hosts:
            if (mtime := _get_mtime(piggybacked_host_source)) is None:
                continue

            if mtime < cut_off_timestamp:
                logger.debug(
                    "Piggyback file '%s' too old (%s). Remove it.",
                    piggybacked_host_source,
                    _render_datetime(mtime),
                )
                _remove_piggyback_file(piggybacked_host_source)

        # Remove empty backed host directory
        try:
            piggybacked_host_folder.rmdir()
        except OSError as e:
            if e.errno == errno.ENOTEMPTY:
                continue
            raise
        logger.debug(
            "Piggyback folder '%s' was empty. Removed it.",
            piggybacked_host_folder,
        )


def _get_mtime(path: Path) -> int | None:
    try:
        # Beware:
        # On POSIX platforms Python reads atime and mtime at nanosecond resolution
        # but only writes them at microsecond resolution.
        # (We're using os.utime() in _store_status_file_of())
        return int(path.stat().st_mtime)
    except FileNotFoundError:
        return None


def _render_datetime(timestamp: float) -> str:
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def move_for_host_rename(omd_root: Path, old_host: str, new_host: str) -> tuple[str, ...]:
    """Move all piggybacked and source files from old_host to new_host

    Return a tuple of strings representing the actions taken.
    """
    piggyback_dir = payload_dir(omd_root)

    def _rename_piggybacked_dir(old_name: str, new_name: str) -> Iterable[str]:
        if not (old_path := piggyback_dir / old_name).exists():
            return

        try:
            shutil.rmtree(str(new_path := piggyback_dir / new_name))
        except FileNotFoundError:
            pass

        os.rename(str(old_path), str(new_path))
        yield "piggyback-load"

    def _rename_payload_file(basedir: Path, old_name: str, new_name: str) -> Iterable[str]:
        if not (old_path := basedir / old_name).exists():
            return

        (new_path := basedir / new_name).unlink(missing_ok=True)
        old_path.rename(new_path)
        yield "piggyback-pig"

    return tuple(
        *_rename_piggybacked_dir(old_host, new_host),
        *_rename_payload_file(piggyback_dir, old_host, new_host),
    )
