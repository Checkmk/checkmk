#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import os
import tempfile
from pathlib import Path
from typing import (
    Container,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
)

import cmk.utils
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.translations
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import VERBOSE
from cmk.utils.regex import regex
from cmk.utils.render import Age
from cmk.utils.type_defs import AgentRawData, HostName

logger = logging.getLogger("cmk.base")


class PiggybackFileInfo(NamedTuple):
    source_hostname: HostName
    file_path: Path
    successfully_processed: bool
    reason: str
    reason_status: int


class PiggybackRawDataInfo(NamedTuple):
    source_hostname: HostName
    file_path: str
    successfully_processed: bool
    reason: str
    reason_status: int
    raw_data: AgentRawData


_PiggybackTimeSetting = Tuple[Optional[str], str, int]

PiggybackTimeSettings = Sequence[_PiggybackTimeSetting]

_PiggybackTimeSettingsMap = Mapping[Tuple[Optional[str], str], int]

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
    piggybacked_hostname: Optional[HostName],
    time_settings: PiggybackTimeSettings,
) -> Sequence[PiggybackRawDataInfo]:
    """Returns the usable piggyback data for the given host

    A list of two element tuples where the first element is
    the source host name and the second element is the raw
    piggyback data (byte string)
    """
    if not piggybacked_hostname:
        return []

    piggyback_file_infos = _get_piggyback_processed_file_infos(piggybacked_hostname, time_settings)
    if not piggyback_file_infos:
        logger.log(
            VERBOSE,
            "No piggyback files for '%s'. Skip processing.",
            piggybacked_hostname,
        )
        return []

    piggyback_data = []
    for file_info in piggyback_file_infos:
        try:
            # Raw data is always stored as bytes. Later the content is
            # converted to unicode in abstact.py:_parse_info which respects
            # 'encoding' in section options.
            raw_data = AgentRawData(store.load_bytes_from_file(file_info.file_path))

        except IOError as e:
            reason = "Cannot read piggyback raw data from source '%s'" % file_info.source_hostname
            piggyback_raw_data = PiggybackRawDataInfo(
                source_hostname=file_info.source_hostname,
                file_path=str(file_info.file_path),
                successfully_processed=False,
                reason=reason,
                reason_status=0,
                raw_data=AgentRawData(b""),
            )
            logger.log(
                VERBOSE,
                "Piggyback file '%s': %s, %s",
                file_info.file_path,
                reason,
                e,
            )

        else:
            piggyback_raw_data = PiggybackRawDataInfo(
                file_info.source_hostname,
                str(file_info.file_path),
                file_info.successfully_processed,
                file_info.reason,
                file_info.reason_status,
                raw_data,
            )
            if file_info.successfully_processed:
                logger.log(
                    VERBOSE,
                    "Piggyback file '%s': %s",
                    file_info.file_path,
                    file_info.reason,
                )
            else:
                logger.log(
                    VERBOSE,
                    "Piggyback file '%s' is outdated (%s). Skip processing.",
                    file_info.file_path,
                    file_info.reason,
                )
        piggyback_data.append(piggyback_raw_data)
    return piggyback_data


def get_source_and_piggyback_hosts(
    time_settings: PiggybackTimeSettings,
) -> Iterator[Tuple[HostName, HostName]]:
    """Generates all piggyback pig/piggybacked host pairs that have up-to-date data"""

    # Pylint bug (https://github.com/PyCQA/pylint/issues/1660). Fixed with pylint 2.x
    for piggybacked_host_folder in _get_piggybacked_host_folders():
        for file_info in _get_piggyback_processed_file_infos(
            HostName(piggybacked_host_folder.name),
            time_settings,
        ):
            if not file_info.successfully_processed:
                continue
            yield HostName(file_info.source_hostname), HostName(piggybacked_host_folder.name)


def has_piggyback_raw_data(
    piggybacked_hostname: HostName,
    time_settings: PiggybackTimeSettings,
) -> bool:
    return any(
        fi.successfully_processed
        for fi in _get_piggyback_processed_file_infos(piggybacked_hostname, time_settings)
    )


def _get_piggyback_processed_file_infos(
    piggybacked_hostname: HostName,
    time_settings: PiggybackTimeSettings,
) -> Sequence[PiggybackFileInfo]:
    """Gather a list of piggyback files to read for further processing.

    Please note that there may be multiple parallel calls executing the
    _get_piggyback_processed_file_infos(), store_piggyback_raw_data() or cleanup_piggyback_files()
    functions. Therefor all these functions needs to deal with suddenly vanishing or
    updated files/directories.
    """
    source_hostnames = get_source_hostnames(piggybacked_hostname)
    matching_time_settings = _get_matching_time_settings(
        source_hostnames, piggybacked_hostname, time_settings
    )

    file_infos = []
    for source_hostname in source_hostnames:
        if source_hostname.startswith("."):
            continue

        piggyback_file_path = _get_piggybacked_file_path(source_hostname, piggybacked_hostname)

        successfully_processed, reason, reason_status = _get_piggyback_processed_file_info(
            source_hostname, piggybacked_hostname, piggyback_file_path, matching_time_settings
        )

        piggyback_file_info = PiggybackFileInfo(
            source_hostname, piggyback_file_path, successfully_processed, reason, reason_status
        )
        file_infos.append(piggyback_file_info)
    return file_infos


def _get_matching_time_settings(
    source_hostnames: Container[HostName],
    piggybacked_hostname: HostName,
    time_settings: PiggybackTimeSettings,
) -> _PiggybackTimeSettingsMap:
    matching_time_settings: Dict[Tuple[Optional[str], str], int] = {}
    for expr, key, value in time_settings:
        # expr may be
        #   - None (global settings) or
        #   - 'source-hostname' or
        #   - 'piggybacked-hostname' or
        #   - '~piggybacked-[hH]ostname'
        # the first entry ('piggybacked-hostname' vs '~piggybacked-[hH]ostname') wins
        if expr is None or expr in source_hostnames or expr == piggybacked_hostname:
            matching_time_settings.setdefault((expr, key), value)
        elif expr.startswith("~") and regex(expr[1:]).match(piggybacked_hostname):
            matching_time_settings.setdefault((piggybacked_hostname, key), value)
    return matching_time_settings


def _get_piggyback_processed_file_info(
    source_hostname: HostName,
    piggybacked_hostname: HostName,
    piggyback_file_path: Path,
    time_settings: _PiggybackTimeSettingsMap,
) -> Tuple[bool, str, int]:

    max_cache_age = _get_max_cache_age(source_hostname, piggybacked_hostname, time_settings)
    validity_period = _get_validity_period(source_hostname, piggybacked_hostname, time_settings)
    validity_state = _get_validity_state(source_hostname, piggybacked_hostname, time_settings)

    try:
        file_age = cmk.utils.cachefile_age(piggyback_file_path)
    except MKGeneralException:
        return False, "Piggyback file might have been deleted", 0

    if file_age > max_cache_age:
        return False, "Piggyback file too old: %s" % Age(file_age - max_cache_age), 0

    status_file_path = _get_source_status_file_path(source_hostname)
    if not status_file_path.exists():
        reason = "Source '%s' not sending piggyback data" % source_hostname
        return _eval_file_in_validity_period(file_age, validity_period, validity_state, reason)

    if _is_piggyback_file_outdated(status_file_path, piggyback_file_path):
        reason = "Piggyback file not updated by source '%s'" % source_hostname
        return _eval_file_in_validity_period(file_age, validity_period, validity_state, reason)

    return True, "Successfully processed from source '%s'" % source_hostname, 0


def _get_max_cache_age(
    source_hostname: HostName,
    piggybacked_hostname: HostName,
    time_settings: _PiggybackTimeSettingsMap,
) -> int:
    key = "max_cache_age"
    dflt: int = time_settings[(None, key)]
    return time_settings.get(
        (piggybacked_hostname, key), time_settings.get((source_hostname, key), dflt)
    )


def _get_validity_period(
    source_hostname: HostName,
    piggybacked_hostname: HostName,
    time_settings: _PiggybackTimeSettingsMap,
) -> Optional[int]:
    key = "validity_period"
    dflt: Optional[int] = time_settings.get((None, key))
    return time_settings.get(
        (piggybacked_hostname, key), time_settings.get((source_hostname, key), dflt)
    )


def _get_validity_state(
    source_hostname: HostName,
    piggybacked_hostname: HostName,
    time_settings: _PiggybackTimeSettingsMap,
) -> int:
    key = "validity_state"
    dflt = 0
    return time_settings.get(
        (piggybacked_hostname, key), time_settings.get((source_hostname, key), dflt)
    )


def _eval_file_in_validity_period(
    file_age: float,
    validity_period: Optional[int],
    validity_state: int,
    reason: str,
) -> Tuple[bool, str, int]:
    if validity_period is not None and file_age < validity_period:
        return (
            True,
            "%s (still valid, %s left)" % (reason, Age(validity_period - file_age)),
            validity_state,
        )
    return False, reason, 0


def _is_piggyback_file_outdated(
    status_file_path: Path,
    piggyback_file_path: Path,
) -> bool:
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
    piggyback_file_paths = []
    for piggybacked_hostname, lines in piggybacked_raw_data.items():
        piggyback_file_path = _get_piggybacked_file_path(source_hostname, piggybacked_hostname)
        logger.log(
            VERBOSE,
            "Storing piggyback data for: %s",
            piggybacked_hostname,
        )
        # Raw data is always stored as bytes. Later the content is
        # converted to unicode in abstact.py:_parse_info which respects
        # 'encoding' in section options.
        store.save_bytes_to_file(piggyback_file_path, b"%s\n" % b"\n".join(lines))
        piggyback_file_paths.append(piggyback_file_path)

    # Store the last contact with this piggyback source to be able to filter outdated data later
    # We use the mtime of this file later for comparison.
    # Only do this for hosts that sent piggyback data this turn, cleanup the status file when no
    # piggyback data was sent this turn.
    if piggybacked_raw_data:
        logger.log(VERBOSE, "Received piggyback data for %d hosts", len(piggybacked_raw_data))

        status_file_path = _get_source_status_file_path(source_hostname)
        _store_status_file_of(status_file_path, piggyback_file_paths)
    else:
        logger.debug("Received no piggyback data")
        remove_source_status_file(source_hostname)


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
        "wb",
        dir=str(status_file_path.parent),
        prefix=".%s.new" % status_file_path.name,
        delete=False,
    ) as tmp:
        tmp_path = tmp.name
        os.chmod(tmp_path, 0o660)
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


def get_source_hostnames(piggybacked_hostname: Optional[HostName] = None) -> Sequence[HostName]:
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
    piggybacked_hostname: HostName,
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

    logger.log(
        VERBOSE,
        "Cleanup piggyback files; time settings: %s.",
        time_settings,
    )

    piggybacked_hosts_settings = _get_piggybacked_hosts_settings(time_settings)

    _cleanup_old_source_status_files(piggybacked_hosts_settings)
    _cleanup_old_piggybacked_files(piggybacked_hosts_settings)


def _get_piggybacked_hosts_settings(
    time_settings: PiggybackTimeSettings,
) -> Sequence[Tuple[Path, Sequence[Path], _PiggybackTimeSettingsMap]]:
    piggybacked_hosts_settings = []
    for piggybacked_host_folder in _get_piggybacked_host_folders():
        source_hosts = _files_in(piggybacked_host_folder)
        matching_time_settings = _get_matching_time_settings(
            [HostName(source_host.name) for source_host in source_hosts],
            HostName(piggybacked_host_folder.name),
            time_settings,
        )
        piggybacked_hosts_settings.append(
            (piggybacked_host_folder, source_hosts, matching_time_settings)
        )
    return piggybacked_hosts_settings


def _cleanup_old_source_status_files(
    piggybacked_hosts_settings: Iterable[Tuple[Path, Iterable[Path], _PiggybackTimeSettingsMap]]
) -> None:
    """Remove source status files which exceed configured maximum cache age.
    There may be several 'Piggybacked Host Files' rules where the max age is configured.
    We simply use the greatest one per source."""

    max_cache_age_by_sources: Dict[str, int] = {}
    for piggybacked_host_folder, source_hosts, time_settings in piggybacked_hosts_settings:
        for source_host in source_hosts:
            max_cache_age = _get_max_cache_age(
                HostName(source_host.name),
                HostName(piggybacked_host_folder.name),
                time_settings,
            )

            max_cache_age_of_source = max_cache_age_by_sources.get(source_host.name)
            if max_cache_age_of_source is None:
                max_cache_age_by_sources[source_host.name] = max_cache_age

            elif max_cache_age >= max_cache_age_of_source:
                max_cache_age_by_sources[source_host.name] = max_cache_age

    for source_state_file in _get_source_state_files():
        try:
            file_age = cmk.utils.cachefile_age(source_state_file)
        except MKGeneralException:
            continue  # File might've been deleted. That's ok.

        # No entry -> no file
        max_cache_age_of_source = max_cache_age_by_sources.get(source_state_file.name)
        if max_cache_age_of_source is None:
            logger.log(
                VERBOSE,
                "No piggyback data from source '%s'",
                source_state_file.name,
            )
            continue

        if file_age > max_cache_age_of_source:
            logger.log(
                VERBOSE,
                "Piggyback source status file '%s' is outdated (File too old: %s). Remove it.",
                source_state_file,
                Age(file_age - max_cache_age_of_source),
            )
            _remove_piggyback_file(source_state_file)


def _cleanup_old_piggybacked_files(
    piggybacked_hosts_settings: Iterable[Tuple[Path, Iterable[Path], _PiggybackTimeSettingsMap]]
) -> None:
    """Remove piggybacked data files which exceed configured maximum cache age."""

    for piggybacked_host_folder, source_hosts, time_settings in piggybacked_hosts_settings:
        for piggybacked_host_source in source_hosts:
            successfully_processed, reason, _reason_status = _get_piggyback_processed_file_info(
                HostName(piggybacked_host_source.name),
                HostName(piggybacked_host_folder.name),
                piggybacked_host_source,
                time_settings=time_settings,
            )

            if not successfully_processed:
                logger.log(
                    VERBOSE,
                    "Piggyback file '%s' is outdated (%s). Remove it.",
                    piggybacked_host_source,
                    reason,
                )
                _remove_piggyback_file(piggybacked_host_source)

        # Remove empty backed host directory
        try:
            piggybacked_host_folder.rmdir()
        except OSError as e:
            if e.errno == errno.ENOTEMPTY:
                continue
            raise
        else:
            logger.log(
                VERBOSE,
                "Piggyback folder '%s' is empty. Removed it.",
                piggybacked_host_folder,
            )
