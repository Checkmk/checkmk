#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import errno
import json
import logging
import os
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import NamedTuple, Self

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.paths import piggyback_dir, piggyback_source_dir
from cmk.utils.store import load_bytes_from_file, makedirs, save_bytes_to_file

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class PiggybackFileInfo:
    source: HostName
    file_path: Path
    last_update: int
    last_contact: int | None

    def serialize(self) -> str:
        return json.dumps({k: str(v) for k, v in asdict(self).items()})

    @classmethod
    def deserialize(cls, serialized: str, /) -> Self:
        raw = json.loads(serialized)
        return cls(
            source=HostName(raw["source"]),
            file_path=Path(raw["file_path"]),
            last_update=int(raw["last_update"]),
            last_contact=None if (i := raw["last_contact"]) is None else int(i),
        )


class PiggybackRawDataInfo(NamedTuple):
    info: PiggybackFileInfo
    raw_data: AgentRawData


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


def get_piggyback_raw_data(piggybacked_hostname: HostAddress) -> Sequence[PiggybackRawDataInfo]:
    """Returns the usable piggyback data for the given host

    A list of two element tuples where the first element is
    the source host name and the second element is the raw
    piggyback data (byte string)
    """
    piggyback_file_infos = _get_payload_meta_data(piggybacked_hostname)
    logger.debug("%s piggyback files for '%s'.", len(piggyback_file_infos), piggybacked_hostname)

    piggyback_data = []
    for file_info in piggyback_file_infos:
        try:
            # Raw data is always stored as bytes. Later the content is
            # converted to unicode in abstact.py:_parse_info which respects
            # 'encoding' in section options.
            content = load_bytes_from_file(file_info.file_path)

        except FileNotFoundError:
            # race condition: file was removed between listing and reading
            continue

        logger.debug("Read piggyback file '%s'", file_info.file_path)
        piggyback_data.append(PiggybackRawDataInfo(info=file_info, raw_data=AgentRawData(content)))
    return piggyback_data


def get_piggybacked_host_with_sources() -> Mapping[HostAddress, Sequence[PiggybackFileInfo]]:
    """Generates all piggyback pig/piggybacked host pairs"""
    return {
        piggybacked_host: _get_payload_meta_data(piggybacked_host)
        for piggybacked_host_folder in _get_piggybacked_host_folders()
        if (piggybacked_host := HostAddress(piggybacked_host_folder.name))
    }


def _remove_piggyback_file(piggyback_file_path: Path) -> bool:
    try:
        piggyback_file_path.unlink()
        return True
    except FileNotFoundError:
        return False


def remove_source_status_file(source_hostname: HostName) -> bool:
    """Remove the source_status_file of this piggyback host which will
    mark the piggyback data from this source as outdated."""
    source_status_path = _get_source_status_file_path(source_hostname)
    return _remove_piggyback_file(source_status_path)


def store_piggyback_raw_data(
    source_hostname: HostName,
    piggybacked_raw_data: Mapping[HostName, Sequence[bytes]],
) -> None:
    if not piggybacked_raw_data:
        # Cleanup the status file when no piggyback data was sent this turn.
        logger.debug("Received no piggyback data")
        remove_source_status_file(source_hostname)
        return

    piggyback_file_paths = []
    for piggybacked_hostname, lines in piggybacked_raw_data.items():
        piggyback_file_path = _get_piggybacked_file_path(source_hostname, piggybacked_hostname)
        logger.debug("Storing piggyback data for: %r", piggybacked_hostname)
        # Raw data is always stored as bytes. Later the content is
        # converted to unicode in abstact.py:_parse_info which respects
        # 'encoding' in section options.
        save_bytes_to_file(piggyback_file_path, b"%s\n" % b"\n".join(lines))
        piggyback_file_paths.append(piggyback_file_path)

    # Store the last contact with this piggyback source to be able to filter outdated data later
    # We use the mtime of this file later for comparison.
    # Only do this for hosts that sent piggyback data this turn.
    logger.debug("Received piggyback data for %d hosts", len(piggybacked_raw_data))
    status_file_path = _get_source_status_file_path(source_hostname)
    _store_status_file_of(status_file_path, piggyback_file_paths)


def _store_status_file_of(
    status_file_path: Path,
    piggyback_file_paths: Iterable[Path],
) -> None:
    makedirs(status_file_path.parent)

    # Cannot use store.save_bytes_to_file like:
    # 1. store.save_bytes_to_file(status_file_path, b"")
    # 2. set utime of piggybacked host files
    # Between 1. and 2.:
    # - the piggybacked host may check its files
    # - status file is newer (before utime of piggybacked host files is set)
    # => piggybacked host file is outdated
    with tempfile.NamedTemporaryFile(
        "wb", dir=str(status_file_path.parent), prefix=f".{status_file_path.name}.new", delete=False
    ) as tmp:
        tmp_path = tmp.name
        tmp.write(b"")

        tmp_stats = os.stat(tmp_path)
        status_file_times = (tmp_stats.st_atime, tmp_stats.st_mtime)
        for piggyback_file_path in piggyback_file_paths:
            try:
                # TODO use Path.stat() but be aware of:
                # On POSIX platforms Python reads atime and mtime at nanosecond resolution
                # but only writes them at microsecond resolution.
                # (We're using os.utime() in _store_status_file_of())
                os.utime(str(piggyback_file_path), status_file_times)
            except FileNotFoundError:
                continue
    os.rename(tmp_path, str(status_file_path))


#   .--folders/files-------------------------------------------------------.
#   |         __       _     _                  ____ _ _                   |
#   |        / _| ___ | | __| | ___ _ __ ___   / / _(_) | ___  ___         |
#   |       | |_ / _ \| |/ _` |/ _ \ '__/ __| / / |_| | |/ _ \/ __|        |
#   |       |  _| (_) | | (_| |  __/ |  \__ \/ /|  _| | |  __/\__ \        |
#   |       |_|  \___/|_|\__,_|\___|_|  |___/_/ |_| |_|_|\___||___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _get_payload_meta_data(piggybacked_hostname: HostName) -> Sequence[PiggybackFileInfo]:
    """Gather a list of piggyback files to read for further processing.

    Please note that there may be multiple parallel calls executing
    store_piggyback_raw_data() or cleanup_piggyback_files() functions.
    All these functions need to deal with suddenly vanishing or updated files/directories.
    """
    piggybacked_host_folder = piggyback_dir / Path(piggybacked_hostname)
    meta_data = []
    for payload_file in _files_in(piggybacked_host_folder):
        source = HostAddress(payload_file.name)
        status_file_path = _get_source_status_file_path(source)

        if (mtime := _get_mtime(payload_file)) is None:
            continue

        meta_data.append(
            PiggybackFileInfo(
                source=source,
                file_path=payload_file,
                last_update=mtime,
                last_contact=_get_mtime(status_file_path),
            )
        )
    return meta_data


def _get_piggybacked_host_folders() -> Sequence[Path]:
    return _files_in(piggyback_dir)


def _get_source_state_files() -> Sequence[Path]:
    return _files_in(piggyback_source_dir)


def _files_in(path: Path) -> Sequence[Path]:
    """Return a sorted sequence of files in `path` excluding hidden files.

    While the order of the files _should_ not matter, in some weird cases it might.
    We don't expect that to happen (let alone be noticed), but in case it *does* happen, at least be predictable.
    """
    try:
        return sorted(f for f in path.iterdir() if not f.name.startswith("."))
    except FileNotFoundError:
        return []


def _get_source_status_file_path(source_hostname: HostName) -> Path:
    return piggyback_source_dir / str(source_hostname)


def _get_piggybacked_file_path(
    source_hostname: HostName,
    piggybacked_hostname: HostName | HostAddress,
) -> Path:
    return piggyback_dir / piggybacked_hostname / source_hostname


# .
#   .--clean up------------------------------------------------------------.
#   |                     _                                                |
#   |                 ___| | ___  __ _ _ __    _   _ _ __                  |
#   |                / __| |/ _ \/ _` | '_ \  | | | | '_ \                 |
#   |               | (__| |  __/ (_| | | | | | |_| | |_) |                |
#   |                \___|_|\___|\__,_|_| |_|  \__,_| .__/                 |
#   |                                               |_|                    |
#   '----------------------------------------------------------------------'


def cleanup_piggyback_files(cut_off_timestamp: float) -> None:
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
        for piggybacked_host_folder in _get_piggybacked_host_folders()
    ]

    _cleanup_old_source_status_files(_get_source_state_files(), cut_off_timestamp)
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
