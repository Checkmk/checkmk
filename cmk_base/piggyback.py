#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import errno
import os
import tempfile
from typing import (  # pylint: disable=unused-import
    Optional, Dict, Set, Iterator, List, Tuple, NamedTuple,
)
from pathlib2 import Path  # pylint: disable=unused-import

import cmk.utils.paths
import cmk.utils.translations
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.render import Age

import cmk_base.utils
import cmk_base.console as console

PiggybackFileInfo = NamedTuple('PiggybackFileInfo', [
    ('source_hostname', str),
    ('file_path', str),
    ('successfully_processed', bool),
    ('reason', str),
    ('reason_status', int),
])

PiggybackRawDataInfo = NamedTuple('PiggybackRawData', [
    ('source_hostname', str),
    ('file_path', str),
    ('successfully_processed', bool),
    ('reason', str),
    ('reason_status', int),
    ('raw_data', str),
])


def get_piggyback_raw_data(piggybacked_hostname, time_settings):
    # type: (str, Dict[Tuple[Optional[str], str], int]) -> List[PiggybackRawDataInfo]
    """Returns the usable piggyback data for the given host

    A list of two element tuples where the first element is
    the source host name and the second element is the raw
    piggyback data (byte string)
    """
    if not piggybacked_hostname:
        return []

    piggyback_file_infos = _get_piggyback_processed_file_infos(piggybacked_hostname, time_settings)
    if not piggyback_file_infos:
        console.verbose("No piggyback files for '%s'. Skip processing.\n" % piggybacked_hostname)
        return []

    piggyback_data = []
    for file_info in piggyback_file_infos:
        try:
            raw_data = open(file_info.file_path).read()

        except IOError as e:
            reason = "Cannot read piggyback raw data from source '%s'" % file_info.source_hostname
            piggyback_raw_data = PiggybackRawDataInfo(source_hostname=file_info.source_hostname,
                                                      file_path=file_info.file_path,
                                                      successfully_processed=False,
                                                      reason=reason,
                                                      reason_status=0,
                                                      raw_data='')
            console.verbose("Piggyback file '%s': %s, %s\n" % (file_info.file_path, reason, e))

        else:
            piggyback_raw_data = PiggybackRawDataInfo(file_info.source_hostname,
                                                      file_info.file_path,
                                                      file_info.successfully_processed,
                                                      file_info.reason, file_info.reason_status,
                                                      raw_data)
            if file_info.successfully_processed:
                console.verbose("Piggyback file '%s': %s.\n" %
                                (file_info.file_path, file_info.reason))
            else:
                console.verbose("Piggyback file '%s' is outdated (%s). Skip processing.\n" %
                                (file_info.file_path, file_info.reason))
        piggyback_data.append(piggyback_raw_data)
    return piggyback_data


def get_source_and_piggyback_hosts(time_settings):
    # type: (Dict[Tuple[Optional[str], str], int]) -> Iterator[Tuple[str, str]]
    """Generates all piggyback pig/piggybacked host pairs that have up-to-date data"""

    # Pylint bug (https://github.com/PyCQA/pylint/issues/1660). Fixed with pylint 2.x
    for piggyback_folder in _get_piggybacked_host_folders():
        piggybacked_hostname = piggyback_folder.name
        for file_info in _get_piggyback_processed_file_infos(piggybacked_hostname, time_settings):
            if not file_info.successfully_processed:
                continue
            yield file_info.source_hostname, piggybacked_hostname


def has_piggyback_raw_data(piggybacked_hostname, time_settings):
    # type: (str, Dict[Tuple[Optional[str], str], int]) -> bool
    for file_info in _get_piggyback_processed_file_infos(piggybacked_hostname, time_settings):
        if file_info.successfully_processed:
            return True
    return False


def _get_piggyback_processed_file_infos(piggybacked_hostname, time_settings):
    # type: (str, Dict[Tuple[Optional[str], str], int]) -> List[PiggybackFileInfo]
    """Gather a list of piggyback files to read for further processing.

    Please note that there may be multiple parallel calls executing the
    _get_piggyback_processed_file_infos(), store_piggyback_raw_data() or cleanup_piggyback_files()
    functions. Therefor all these functions needs to deal with suddenly vanishing or
    updated files/directories.
    """
    source_hostnames = get_source_hostnames(piggybacked_hostname)

    file_infos = []  # type: List[PiggybackFileInfo]
    for source_hostname in source_hostnames:
        if source_hostname.startswith("."):
            continue

        piggyback_file_path = _get_piggybacked_file_path(source_hostname, piggybacked_hostname)

        successfully_processed, reason, reason_status = _get_piggyback_processed_file_info(
            source_hostname, piggybacked_hostname, piggyback_file_path, time_settings)

        piggyback_file_info = PiggybackFileInfo(source_hostname, piggyback_file_path,
                                                successfully_processed, reason, reason_status)
        file_infos.append(piggyback_file_info)
    return file_infos


def _get_piggyback_processed_file_info(source_hostname, piggybacked_hostname, piggyback_file_path,
                                       time_settings):
    # type: (str, str, str, Dict[Tuple[Optional[str], str], int]) -> Tuple[bool, str, int]

    max_cache_age = _get_max_cache_age(source_hostname, piggybacked_hostname, time_settings)
    validity_period = _get_validity_period(source_hostname, piggybacked_hostname, time_settings)
    validity_state = _get_validity_state(source_hostname, piggybacked_hostname, time_settings)

    try:
        file_age = cmk_base.utils.cachefile_age(piggyback_file_path)
    except MKGeneralException:
        return False, "Piggyback file might have been deleted", 0

    if file_age > max_cache_age:
        return False, "Piggyback file too old: %s" % Age(file_age - max_cache_age), 0

    status_file_path = _get_source_status_file_path(source_hostname)
    if not os.path.exists(status_file_path):
        reason = "Source '%s' not sending piggyback data" % source_hostname
        return _eval_file_in_validity_period(file_age, validity_period, validity_state, reason)

    if _is_piggyback_file_outdated(status_file_path, piggyback_file_path):
        reason = "Piggyback file not updated by source '%s'" % source_hostname
        return _eval_file_in_validity_period(file_age, validity_period, validity_state, reason)

    return True, "Successfully processed from source '%s'" % source_hostname, 0


def _get_max_cache_age(source_hostname, piggybacked_hostname, time_settings):
    # type: (str, str, Dict[Tuple[Optional[str], str], int]) -> int
    key = 'max_cache_age'
    dflt = time_settings[(None, key)]  # type: int
    return time_settings.get((piggybacked_hostname, key),
                             time_settings.get((source_hostname, key), dflt))


def _get_validity_period(source_hostname, piggybacked_hostname, time_settings):
    # type: (str, str, Dict[Tuple[Optional[str], str], int]) -> Optional[int]
    key = 'validity_period'
    dflt = time_settings.get((None, key))  # type: Optional[int]
    return time_settings.get((piggybacked_hostname, key),
                             time_settings.get((source_hostname, key), dflt))


def _get_validity_state(source_hostname, piggybacked_hostname, time_settings):
    # type: (str, str, Dict[Tuple[Optional[str], str], int]) -> int
    key = 'validity_state'
    dflt = 0
    return time_settings.get((piggybacked_hostname, key),
                             time_settings.get((source_hostname, key), dflt))


def _eval_file_in_validity_period(file_age, validity_period, validity_state, reason):
    # type: (int, Optional[int], int, str) -> Tuple[bool, str, int]
    if validity_period is not None and file_age < validity_period:
        return (True, "%s (still valid, %s left)" % (reason, Age(validity_period - file_age)),
                validity_state)
    return False, reason, 0


def _is_piggyback_file_outdated(status_file_path, piggyback_file_path):
    # type: (str, str) -> bool
    try:
        # On POSIX platforms Python reads atime and mtime at nanosecond resolution
        # but only writes them at microsecond resolution.
        # (We're using os.utime() in _store_status_file_of())
        return os.stat(status_file_path)[8] > os.stat(piggyback_file_path)[8]
    except OSError as e:
        if e.errno == errno.ENOENT:
            return True
        else:
            raise


def _remove_piggyback_file(piggyback_file_path):
    # type: (str) -> bool
    try:
        os.remove(piggyback_file_path)
        return True
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False
        else:
            raise


def remove_source_status_file(source_hostname):
    # type: (str) -> bool
    """Remove the source_status_file of this piggyback host which will
    mark the piggyback data from this source as outdated."""
    source_status_path = _get_source_status_file_path(source_hostname)
    return _remove_piggyback_file(source_status_path)


def store_piggyback_raw_data(source_hostname, piggybacked_raw_data):
    # type: (str, Dict[str, List[str]]) -> None
    piggyback_file_paths = []
    for piggybacked_hostname, lines in piggybacked_raw_data.items():
        piggyback_file_path = _get_piggybacked_file_path(source_hostname, piggybacked_hostname)
        console.verbose("Storing piggyback data for: %s\n" % piggybacked_hostname)
        content = "\n".join(lines) + "\n"
        store.save_file(piggyback_file_path, content)
        piggyback_file_paths.append(piggyback_file_path)

    # Store the last contact with this piggyback source to be able to filter outdated data later
    # We use the mtime of this file later for comparison.
    # Only do this for hosts that sent piggyback data this turn, cleanup the status file when no
    # piggyback data was sent this turn.
    if piggybacked_raw_data:
        status_file_path = _get_source_status_file_path(source_hostname)
        _store_status_file_of(status_file_path, piggyback_file_paths)
    else:
        remove_source_status_file(source_hostname)


def _store_status_file_of(status_file_path, piggyback_file_paths):
    # type: (str, List[str]) -> None
    store.makedirs(os.path.dirname(status_file_path))
    with tempfile.NamedTemporaryFile("w",
                                     dir=os.path.dirname(status_file_path),
                                     prefix=".%s.new" % os.path.basename(status_file_path),
                                     delete=False) as tmp:
        tmp_path = tmp.name
        os.chmod(tmp_path, 0o660)
        tmp.write("")

        tmp_stats = os.stat(tmp_path)
        status_file_times = (tmp_stats.st_atime, tmp_stats.st_mtime)
        for piggyback_file_path in piggyback_file_paths:
            try:
                os.utime(piggyback_file_path, status_file_times)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    continue
                else:
                    raise
    os.rename(tmp_path, status_file_path)


#   .--folders/files-------------------------------------------------------.
#   |         __       _     _                  ____ _ _                   |
#   |        / _| ___ | | __| | ___ _ __ ___   / / _(_) | ___  ___         |
#   |       | |_ / _ \| |/ _` |/ _ \ '__/ __| / / |_| | |/ _ \/ __|        |
#   |       |  _| (_) | | (_| |  __/ |  \__ \/ /|  _| | |  __/\__ \        |
#   |       |_|  \___/|_|\__,_|\___|_|  |___/_/ |_| |_|_|\___||___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def get_source_hostnames(piggybacked_hostname=None):
    # type: (Optional[str]) -> List[str]
    if piggybacked_hostname is None:
        return [
            source_host.name
            for piggybacked_host_folder in _get_piggybacked_host_folders()
            for source_host in _get_piggybacked_host_sources(piggybacked_host_folder)
        ]

    piggybacked_host_folder = cmk.utils.paths.piggyback_dir / Path(piggybacked_hostname)
    return [
        source_host.name for source_host in _get_piggybacked_host_sources(piggybacked_host_folder)
    ]


def _get_piggybacked_host_folders():
    # type: () -> List[Path]
    try:
        return list(cmk.utils.paths.piggyback_dir.iterdir())
    except OSError as e:
        if e.errno == errno.ENOENT:
            return []
        else:
            raise


def _get_piggybacked_host_sources(piggybacked_host_folder):
    # type: (Path) -> List[Path]
    try:
        return list(piggybacked_host_folder.iterdir())
    except OSError as e:
        if e.errno == errno.ENOENT:
            return []
        else:
            raise


def _get_source_status_file_path(source_hostname):
    # type: (str) -> str
    return str(cmk.utils.paths.piggyback_source_dir / source_hostname)


def _get_piggybacked_file_path(source_hostname, piggybacked_hostname):
    # type: (str, str) -> str
    return str(cmk.utils.paths.piggyback_dir / piggybacked_hostname / source_hostname)


#.
#   .--clean up------------------------------------------------------------.
#   |                     _                                                |
#   |                 ___| | ___  __ _ _ __    _   _ _ __                  |
#   |                / __| |/ _ \/ _` | '_ \  | | | | '_ \                 |
#   |               | (__| |  __/ (_| | | | | | |_| | |_) |                |
#   |                \___|_|\___|\__,_|_| |_|  \__,_| .__/                 |
#   |                                               |_|                    |
#   '----------------------------------------------------------------------'


def cleanup_piggyback_files(time_settings):
    # type: (Dict[Tuple[Optional[str], str], int]) -> None
    """This is a housekeeping job to clean up different old files from the
    piggyback directories.

    # Source status files and/or piggybacked data files are cleaned up/deleted
    # if and only if they have exceeded the maximum cache age configured in the
    # global settings or in the rule 'Piggybacked Host Files'."""

    console.verbose("Cleanup piggyback files; time settings: %s.\n" % repr(time_settings))

    _cleanup_old_source_status_files(time_settings)
    _cleanup_old_piggybacked_files(time_settings)


def _cleanup_old_source_status_files(time_settings):
    # type: (Dict[Tuple[Optional[str], str], int]) -> None
    """Remove source status files which exceed configured maximum cache age.
    There may be several 'Piggybacked Host Files' rules where the max age is configured.
    We simply use the greatest one per source."""

    global_max_cache_age = time_settings[(None, 'max_cache_age')]  # type: int

    max_cache_age_by_sources = {}  # type: Dict[str, int]
    for piggybacked_host_folder in _get_piggybacked_host_folders():
        for source_host in _get_piggybacked_host_sources(piggybacked_host_folder):
            max_cache_age = _get_max_cache_age(source_host.name, piggybacked_host_folder.name,
                                               time_settings)
            max_cache_age_of_source = max_cache_age_by_sources.get(source_host.name)
            if max_cache_age_of_source is None:
                max_cache_age_by_sources[source_host.name] = max_cache_age

            elif max_cache_age >= max_cache_age_of_source:
                max_cache_age_by_sources[source_host.name] = max_cache_age

    base_dir = str(cmk.utils.paths.piggyback_source_dir)
    for entry in os.listdir(base_dir):
        if entry[0] == ".":
            continue

        source_file_path = os.path.join(base_dir, entry)

        try:
            file_age = cmk_base.utils.cachefile_age(source_file_path)
        except MKGeneralException:
            continue  # File might've been deleted. That's ok.

        max_cache_age = max_cache_age_by_sources.get(entry, global_max_cache_age)
        if file_age > max_cache_age:
            console.verbose(
                "Piggyback source status file '%s' is outdated (File too old: %s). Remove it.\n" %
                (source_file_path, Age(file_age - max_cache_age)))
            _remove_piggyback_file(source_file_path)


def _cleanup_old_piggybacked_files(time_settings):
    # type: (Dict[Tuple[Optional[str], str], int]) -> None
    """Remove piggybacked data files which exceed configured maximum cache age."""

    base_dir = str(cmk.utils.paths.piggyback_dir)
    for piggybacked_hostname in os.listdir(base_dir):
        if piggybacked_hostname[0] == ".":
            continue

        # Cleanup piggyback files from sources that we have no status file for
        backed_host_dir_path = os.path.join(base_dir, piggybacked_hostname)
        for source_hostname in os.listdir(backed_host_dir_path):
            if source_hostname[0] == ".":
                continue

            piggyback_file_path = os.path.join(backed_host_dir_path, source_hostname)

            successfully_processed, reason, _reason_status =\
                _get_piggyback_processed_file_info(source_hostname, piggybacked_hostname, piggyback_file_path, time_settings)

            if not successfully_processed:
                console.verbose("Piggyback file '%s' is outdated (%s). Remove it.\n" %
                                (piggyback_file_path, reason))
                _remove_piggyback_file(piggyback_file_path)

        # Remove empty backed host directory
        try:
            os.rmdir(backed_host_dir_path)
        except OSError as e:
            if e.errno == errno.ENOTEMPTY:
                pass
            else:
                raise
        else:
            console.verbose("Piggyback folder '%s' is empty. Remove it.\n" % backed_host_dir_path)
