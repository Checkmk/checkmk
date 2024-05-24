#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import errno
import json
import logging
import os
import re
import tempfile
import time
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, NamedTuple, Self

import cmk.utils
import cmk.utils.paths
from cmk.utils import store
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.hostaddress import HostAddress, HostName

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class _PayloadMetaData:
    source: HostName
    target: HostName
    file_path: Path
    mtime: float
    abandoned: bool


@dataclass(frozen=True, kw_only=True)
class PiggybackFileInfo:
    source: HostName
    file_path: Path
    last_update: float
    valid: bool
    message: str
    status: int

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError(self.message)

    def serialize(self) -> str:
        return json.dumps({k: str(v) for k, v in asdict(self).items()})

    @classmethod
    def deserialize(cls, serialized: str, /) -> Self:
        raw = json.loads(serialized)
        return cls(
            source=HostName(raw["source"]),
            file_path=Path(raw["file_path"]),
            last_update=float(raw["last_update"]),
            valid=bool(raw["valid"]),
            message=str(raw["message"]),
            status=int(raw["status"]),
        )


class PiggybackRawDataInfo(NamedTuple):
    info: PiggybackFileInfo
    raw_data: AgentRawData


_PiggybackTimeSetting = tuple[str | None, str, int]

PiggybackTimeSettings = Sequence[_PiggybackTimeSetting]

_PiggybackTimeSettingsMap = Mapping[tuple[str | None, str], int]

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


def get_piggyback_raw_data(
    piggybacked_hostname: HostAddress,
    time_settings: PiggybackTimeSettings,
) -> Sequence[PiggybackRawDataInfo]:
    """Returns the usable piggyback data for the given host

    A list of two element tuples where the first element is
    the source host name and the second element is the raw
    piggyback data (byte string)
    """
    piggyback_file_infos = _get_piggyback_processed_file_infos(piggybacked_hostname, time_settings)
    logger.debug("%s piggyback files for '%s'.", len(piggyback_file_infos), piggybacked_hostname)

    piggyback_data = []
    for file_info in piggyback_file_infos:
        try:
            # Raw data is always stored as bytes. Later the content is
            # converted to unicode in abstact.py:_parse_info which respects
            # 'encoding' in section options.
            content = store.load_bytes_from_file(file_info.file_path)

        except FileNotFoundError:
            # race condition: file was removed between listing and reading
            continue

        logger.debug("Piggyback file '%s': %s", file_info.file_path, file_info.message)
        piggyback_data.append(PiggybackRawDataInfo(info=file_info, raw_data=AgentRawData(content)))
    return piggyback_data


def get_piggybacked_host_with_sources(
    time_settings: PiggybackTimeSettings,
) -> Mapping[HostAddress, Sequence[HostAddress]]:
    """Generates all piggyback pig/piggybacked host pairs that have up-to-date data"""

    return {
        piggybacked_host: [
            file_info.source
            for file_info in _get_piggyback_processed_file_infos(piggybacked_host, time_settings)
            if file_info.valid
        ]
        for piggybacked_host_folder in _get_piggybacked_host_folders()
        if (piggybacked_host := HostAddress(piggybacked_host_folder.name))
    }


class Config:
    def __init__(
        self,
        piggybacked_hostname: HostAddress,
        time_settings: PiggybackTimeSettings,
    ) -> None:
        self.piggybacked: Final = piggybacked_hostname
        self._expanded_settings = {
            (host, key): value
            for expr, key, value in reversed(time_settings)
            for host in self._normalize_pattern(expr, piggybacked_hostname)
        }

    @staticmethod
    def _normalize_pattern(
        expr: str | None, piggybacked: HostAddress
    ) -> Iterable[HostAddress | None]:
        # expr may be
        #   - None (global settings) or
        #   - 'source-hostname' or
        #   - 'piggybacked-hostname' or
        #   - '~piggybacked-[hH]ostname'
        # the first entry ('piggybacked-hostname' vs '~piggybacked-[hH]ostname') wins
        if expr is None:
            yield None
        elif not expr.startswith("~"):
            yield HostAddress(expr)
        elif re.match(expr[1:], piggybacked):
            yield piggybacked

    def _lookup(self, key: str, source_hostname: HostAddress) -> int:
        with suppress(KeyError):
            return self._expanded_settings[(self.piggybacked, key)]
        with suppress(KeyError):
            return self._expanded_settings[(source_hostname, key)]

        # TODO: pass the defaults for *all* settings explicitly.
        return self._expanded_settings[(None, key)]

    def max_cache_age(self, source: HostAddress) -> int:
        return self._lookup("max_cache_age", source)

    def validity_period(self, source: HostAddress) -> int | None:
        try:
            return self._lookup("validity_period", source)
        except KeyError:
            return None  # TODO: in fact, we also default to 0 here

    def validity_state(self, source: HostAddress) -> int:
        try:
            return self._lookup("validity_state", source)
        except KeyError:
            return 0


def _get_piggyback_processed_file_infos(
    piggybacked_hostname: HostName | HostAddress,
    time_settings: PiggybackTimeSettings,
) -> Sequence[PiggybackFileInfo]:
    """Gather a list of piggyback files to read for further processing.

    Please note that there may be multiple parallel calls executing the
    _get_piggyback_processed_file_infos(), store_piggyback_raw_data() or cleanup_piggyback_files()
    functions. Therefor all these functions needs to deal with suddenly vanishing or
    updated files/directories.
    """
    payload_meta_data = _get_payload_meta_data(piggybacked_hostname)
    expanded_time_settings = Config(piggybacked_hostname, time_settings)
    return [
        _get_piggyback_processed_file_info(meta, settings=expanded_time_settings)
        for meta in payload_meta_data
    ]


def _get_piggyback_processed_file_info(
    meta: _PayloadMetaData,
    *,
    settings: Config,
) -> PiggybackFileInfo:
    file_age = time.time() - meta.mtime

    if file_age > (allowed := settings.max_cache_age(meta.source)):
        return PiggybackFileInfo(
            source=meta.source,
            file_path=meta.file_path,
            last_update=meta.mtime,
            valid=False,
            message=f"Piggyback file too old (age: {_render_time(file_age)}, allowed: {_render_time(allowed)})",
            status=0,
        )

    validity_period = settings.validity_period(meta.source)
    validity_state = settings.validity_state(meta.source)

    if meta.abandoned:
        valid_msg = _validity_period_message(file_age, validity_period)
        return PiggybackFileInfo(
            source=meta.source,
            file_path=meta.file_path,
            last_update=meta.mtime,
            valid=bool(valid_msg),
            message=(f"Piggyback data not updated by source '{meta.source}'{valid_msg}"),
            status=validity_state if valid_msg else 0,
        )

    return PiggybackFileInfo(
        source=meta.source,
        file_path=meta.file_path,
        last_update=meta.mtime,
        valid=True,
        message=f"Successfully processed from source '{meta.source}'",
        status=0,
    )


def _validity_period_message(
    file_age: float,
    validity_period: int | None,
) -> str:
    if validity_period is None or (time_left := validity_period - file_age) <= 0:
        return ""
    return f" (still valid, {_render_time(time_left)} left)"


def _is_piggybacked_host_abandoned(
    status_file_path: Path,
    piggyback_file_path: Path,
) -> bool:
    """Return True if the status file is missing or it is newer than the payload file

    It will return True if the payload file is "abandoned", i.e. the source host is
    still sending data, but no longer has data for this piggybacked ( = target) host.
    """
    try:
        # TODO use Path.stat() but be aware of:
        # On POSIX platforms Python reads atime and mtime at nanosecond resolution
        # but only writes them at microsecond resolution.
        # (We're using os.utime() in _store_status_file_of())
        return os.stat(str(status_file_path))[8] > os.stat(str(piggyback_file_path))[8]
    except FileNotFoundError:
        return True


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
        store.save_bytes_to_file(piggyback_file_path, b"%s\n" % b"\n".join(lines))
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
    store.makedirs(status_file_path.parent)

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


def _get_payload_meta_data(piggybacked_hostname: HostName) -> Sequence[_PayloadMetaData]:
    piggybacked_host_folder = cmk.utils.paths.piggyback_dir / Path(piggybacked_hostname)
    meta_data = []
    for payload_file in _files_in(piggybacked_host_folder):
        source = HostName(payload_file.name)
        status_file_path = _get_source_status_file_path(source)
        try:
            mtime = payload_file.stat().st_mtime
        except FileNotFoundError:
            continue
        meta_data.append(
            _PayloadMetaData(
                source=source,
                target=piggybacked_hostname,
                file_path=payload_file,
                mtime=mtime,
                abandoned=_is_piggybacked_host_abandoned(status_file_path, payload_file),
            )
        )
    return meta_data


def get_source_hostnames(
    piggybacked_hostname: HostName | HostAddress | None = None,
) -> Sequence[HostName]:
    if piggybacked_hostname is None:
        return [
            HostName(source_host.name)
            for piggybacked_host_folder in _get_piggybacked_host_folders()
            for source_host in _files_in(piggybacked_host_folder)
        ]

    piggybacked_host_folder = cmk.utils.paths.piggyback_dir / Path(piggybacked_hostname)
    return [HostName(source_host.name) for source_host in _files_in(piggybacked_host_folder)]


def _get_piggybacked_host_folders() -> Sequence[Path]:
    return _files_in(cmk.utils.paths.piggyback_dir)


def _get_source_state_files() -> Sequence[Path]:
    return _files_in(cmk.utils.paths.piggyback_source_dir)


def _files_in(path: Path) -> Sequence[Path]:
    try:
        return [f for f in path.iterdir() if not f.name.startswith(".")]
    except FileNotFoundError:
        return []


def _get_source_status_file_path(source_hostname: HostName) -> Path:
    return cmk.utils.paths.piggyback_source_dir / str(source_hostname)


def _get_piggybacked_file_path(
    source_hostname: HostName,
    piggybacked_hostname: HostName | HostAddress,
) -> Path:
    return cmk.utils.paths.piggyback_dir / piggybacked_hostname / source_hostname


# .
#   .--clean up------------------------------------------------------------.
#   |                     _                                                |
#   |                 ___| | ___  __ _ _ __    _   _ _ __                  |
#   |                / __| |/ _ \/ _` | '_ \  | | | | '_ \                 |
#   |               | (__| |  __/ (_| | | | | | |_| | |_) |                |
#   |                \___|_|\___|\__,_|_| |_|  \__,_| .__/                 |
#   |                                               |_|                    |
#   '----------------------------------------------------------------------'


def cleanup_piggyback_files(time_settings: PiggybackTimeSettings) -> None:
    """This is a housekeeping job to clean up different old files from the
    piggyback directories.

    # Source status files and/or piggybacked data files are cleaned up/deleted
    # if and only if they have exceeded the maximum cache age configured in the
    # global settings or in the rule 'Piggybacked Host Files'."""
    logger.debug("Cleanup piggyback files.")
    logger.debug("Time settings: %r.", time_settings)

    piggybacked_hosts_settings = _get_piggybacked_hosts_settings(time_settings)

    _cleanup_old_source_status_files(piggybacked_hosts_settings)
    _cleanup_old_piggybacked_files(piggybacked_hosts_settings)


def _get_piggybacked_hosts_settings(
    time_settings: PiggybackTimeSettings,
) -> Sequence[tuple[Path, Sequence[Path], Config]]:
    piggybacked_hosts_settings = []
    for piggybacked_host_folder in _get_piggybacked_host_folders():
        source_hosts = _files_in(piggybacked_host_folder)
        time_settings_map = Config(
            HostName(piggybacked_host_folder.name),
            time_settings,
        )
        piggybacked_hosts_settings.append(
            (piggybacked_host_folder, source_hosts, time_settings_map)
        )
    return piggybacked_hosts_settings


def _cleanup_old_source_status_files(
    piggybacked_hosts_settings: Iterable[tuple[Path, Iterable[Path], Config]]
) -> None:
    """Remove source status files which exceed configured maximum cache age.
    There may be several 'Piggybacked Host Files' rules where the max age is configured.
    We simply use the greatest one per source."""

    max_cache_age_by_sources: dict[str, int] = {}
    for _piggybacked_host_folder, source_hosts, time_settings in piggybacked_hosts_settings:
        for source_host in source_hosts:
            max_cache_age = time_settings.max_cache_age(
                HostName(source_host.name),
            )

            max_cache_age_of_source = max_cache_age_by_sources.get(source_host.name)
            if max_cache_age_of_source is None or max_cache_age_of_source <= max_cache_age:
                max_cache_age_by_sources[source_host.name] = max_cache_age

    for source_state_file in _get_source_state_files():
        try:
            file_age = _time_since_last_modification(source_state_file)
        except FileNotFoundError:
            continue  # File has been removed, that's OK.

        # No entry -> no file
        max_cache_age_of_source = max_cache_age_by_sources.get(source_state_file.name)
        if max_cache_age_of_source is None:
            logger.debug("No piggyback data from source '%s'", source_state_file.name)
            continue

        if file_age > max_cache_age_of_source:
            logger.debug(
                "Piggyback source status file '%s' too old (age: %s, allowed: %s). Remove it.",
                source_state_file,
                _render_time(file_age),
                _render_time(max_cache_age_of_source),
            )
            _remove_piggyback_file(source_state_file)


def _cleanup_old_piggybacked_files(
    piggybacked_hosts_settings: Iterable[tuple[Path, Iterable[Path], Config]]
) -> None:
    """Remove piggybacked data files which exceed configured maximum cache age."""

    for piggybacked_host_folder, source_hosts, time_settings in piggybacked_hosts_settings:
        for piggybacked_host_source in source_hosts:
            src = HostName(piggybacked_host_source.name)

            try:
                file_age = _time_since_last_modification(piggybacked_host_source)
            except FileNotFoundError:
                continue

            max_cache_age = time_settings.max_cache_age(src)
            validity_period = time_settings.validity_period(src) or 0
            if file_age <= max_cache_age or file_age <= validity_period:
                # Do not remove files just because they're abandoned.
                # We don't use them anymore, but the DCD still needs to know about them for a while.
                continue

            logger.debug("Piggyback file '%s' is outdated. Remove it.", piggybacked_host_source)
            _remove_piggyback_file(piggybacked_host_source)

        # Remove empty backed host directory
        try:
            piggybacked_host_folder.rmdir()
        except OSError as e:
            if e.errno == errno.ENOTEMPTY:
                continue
            raise
        logger.debug(
            "Piggyback folder '%s' is empty. Removed it.",
            piggybacked_host_folder,
        )


def _time_since_last_modification(path: Path) -> float:
    """Return the time difference between the last modification and now.

    Raises:
        FileNotFoundError if `path` does not exist.

    """
    return time.time() - path.stat().st_mtime


def _render_time(value: float | int) -> str:
    """Format time difference seconds into human readable text

    >>> _render_time(184)
    '0:03:04'

    Unlikely in this context, but still acceptable:
    >>> _render_time(92635.3)
    '1 day, 1:43:55'
    """
    return str(datetime.timedelta(seconds=round(value)))
