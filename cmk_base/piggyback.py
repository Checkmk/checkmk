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
from typing import Optional, Dict, Set, Iterator, List, Tuple  # pylint: disable=unused-import

import cmk.utils.paths
import cmk.utils.translations
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.console as console


def get_piggyback_raw_data(hostname, piggyback_max_cachefile_age):
    # type: (str, int) -> List[Tuple[str, str]]
    """Returns the usable piggyback data for the given host

    A list of two element tuples where the first element is
    the source host name and the second element is the raw
    piggyback data (byte string)
    """
    if not hostname:
        return []

    piggyback_data = []
    for source_host, piggyback_file_path in _get_piggyback_files(hostname,
                                                                 piggyback_max_cachefile_age):
        try:
            raw_data = file(piggyback_file_path).read()
        except IOError as e:
            console.verbose("Cannot read piggyback raw data from host %s: %s\n" % (source_host, e))
            continue

        console.verbose("Using piggyback raw data from host %s.\n" % source_host)
        piggyback_data.append((source_host, raw_data))

    return piggyback_data


def get_source_and_piggyback_hosts(piggyback_max_cachefile_age):
    # type: (int) -> Iterator[Tuple[str, str]]
    """Generates all piggyback pig/piggybacked host pairs that have up-to-date data"""
    # Pylint bug (https://github.com/PyCQA/pylint/issues/1660). Fixed with pylint 2.x
    for piggyback_dir in cmk.utils.paths.piggyback_dir.glob("*"):  # pylint: disable=no-member
        piggybacked_host = piggyback_dir.name
        for source_host, _piggyback_file_path in _get_piggyback_files(piggybacked_host,
                                                                      piggyback_max_cachefile_age):
            yield source_host, piggybacked_host


def has_piggyback_raw_data(hostname, piggyback_max_cachefile_age):
    # type: (str, int) -> bool
    return _get_piggyback_files(hostname, piggyback_max_cachefile_age) != []


def _get_piggyback_files(hostname, piggyback_max_cachefile_age):
    # type: (str, int) -> List[Tuple[str, str]]
    """Gather a list of piggyback files to read for further processing.

    Please note that there may be multiple parallel calls executing the
    _get_piggyback_files(), store_piggyback_raw_data() or cleanup_piggyback_files()
    functions. Therefor all these functions needs to deal with suddenly vanishing or
    updated files/directories.
    """
    files = []  # type: List[Tuple[str, str]]
    host_piggyback_dir = cmk.utils.paths.piggyback_dir / hostname

    # cleanup_piggyback_files() may remove stale piggyback files of one source
    # host and also the directory "hostname" when the last piggyback file for the
    # current host was removed. This may cause the os.listdir() to fail. We treat
    # this as regular case: No piggyback files for the current host.
    try:
        source_host_names = [e.name for e in host_piggyback_dir.iterdir()]
    except OSError as e:
        if e.errno == errno.ENOENT:
            return files
        else:
            raise

    for source_host in source_host_names:
        if source_host.startswith("."):
            continue

        piggyback_file_path = host_piggyback_dir / source_host

        try:
            file_age = cmk_base.utils.cachefile_age(str(piggyback_file_path))
        except MKGeneralException:
            continue  # File might've been deleted. That's ok.

        # Skip piggyback files that are outdated at all
        if file_age > piggyback_max_cachefile_age:
            console.verbose(
                "Piggyback file %s is outdated (%d seconds too old). Skip processing.\n" %
                (piggyback_file_path, file_age - piggyback_max_cachefile_age))
            continue

        status_file_path = _piggyback_source_status_path(source_host)
        if not os.path.exists(status_file_path):
            console.verbose(
                "Piggyback file %s is outdated (Source not sending piggyback). Skip processing.\n" %
                piggyback_file_path)
            continue

        if _is_piggyback_file_outdated(status_file_path, str(piggyback_file_path)):
            console.verbose(
                "Piggyback file %s is outdated (Not updated by source). Skip processing.\n" %
                piggyback_file_path)
            continue

        files.append((source_host, str(piggyback_file_path)))

    return files


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


def _piggyback_source_status_path(source_host):
    # type: (str) -> str
    return str(cmk.utils.paths.piggyback_source_dir / source_host)


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


def remove_source_status_file(source_host):
    # type: (str) -> bool
    """Remove the source_status_file of this piggyback host which will
    mark the piggyback data from this source as outdated."""
    source_status_path = _piggyback_source_status_path(source_host)
    return _remove_piggyback_file(source_status_path)


def store_piggyback_raw_data(source_host, piggybacked_raw_data):
    # type: (str, Dict[str, str]) -> None
    piggyback_file_paths = []
    for piggybacked_host, lines in piggybacked_raw_data.items():
        piggyback_file_path = str(cmk.utils.paths.piggyback_dir / piggybacked_host / source_host)
        console.verbose("Storing piggyback data for: %s\n" % piggybacked_host)
        content = "\n".join(lines) + "\n"
        store.save_file(piggyback_file_path, content)
        piggyback_file_paths.append(piggyback_file_path)

    # Store the last contact with this piggyback source to be able to filter outdated data later
    # We use the mtime of this file later for comparison.
    # Only do this for hosts that sent piggyback data this turn, cleanup the status file when no
    # piggyback data was sent this turn.
    if piggybacked_raw_data:
        status_file_path = _piggyback_source_status_path(source_host)
        _store_status_file_of(status_file_path, piggyback_file_paths)
    else:
        remove_source_status_file(source_host)


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


def cleanup_piggyback_files(piggyback_max_cachefile_age):
    # type: (int) -> None
    """This is a housekeeping job to clean up different old files from the
    piggyback directories.

    # Cleanup piggyback data of hosts that are not sending piggyback data anymore
    # a) hosts that have a file below piggyback_sources:
    #    -> check age of the file and remove it once it reached piggyback_max_cachefile_age
    # b) hosts that don't have a file below piggyback_sources (old version or removed by step "a)"):
    #    -> remove all piggyback_raw_data files created by this source

    # Cleanup empty backed host directories below "piggyback"

    Please note that there may be multiple parallel calls executing the
    _get_piggyback_files(), store_piggyback_raw_data() or cleanup_piggyback_files()
    functions. Therefor all these functions needs to deal with suddenly vanishing or
    updated files/directories.
    """
    _cleanup_old_source_status_files(piggyback_max_cachefile_age)
    _cleanup_old_piggybacked_files(piggyback_max_cachefile_age)


def _cleanup_old_source_status_files(piggyback_max_cachefile_age):
    # type: (int) -> None
    base_dir = str(cmk.utils.paths.piggyback_source_dir)
    for entry in os.listdir(base_dir):
        if entry[0] == ".":
            continue

        piggyback_file_path = os.path.join(base_dir, entry)

        try:
            file_age = cmk_base.utils.cachefile_age(piggyback_file_path)
        except MKGeneralException:
            continue  # File might've been deleted. That's ok.

        if file_age > piggyback_max_cachefile_age:
            console.verbose("Removing outdated piggyback source status file %s\n" %
                            piggyback_file_path)
            _remove_piggyback_file(piggyback_file_path)


def _cleanup_old_piggybacked_files(piggyback_max_cachefile_age):
    # type: (int) -> None
    """Remove piggyback data that is not needed anymore

    The monitoring (_get_piggyback_files()) is already skipping these files,
    but we need some cleanup mechanism.

    - Remove all piggyback files created by sources without status file
    - Remove all piggyback files that are older that the current status file of the source host
    - Cleanup empty backed host directories below "piggyback"
    """
    keep_sources = set(os.listdir(str(cmk.utils.paths.piggyback_source_dir)))

    base_dir = os.path.join(cmk.utils.paths.tmp_dir, "piggyback")
    for backed_host_name in os.listdir(base_dir):
        if backed_host_name[0] == ".":
            continue

        # Cleanup piggyback files from sources that we have no status file for
        backed_host_dir_path = os.path.join(base_dir, backed_host_name)
        for source_host_name in os.listdir(backed_host_dir_path):
            if source_host_name[0] == ".":
                continue

            piggyback_file_path = os.path.join(backed_host_dir_path, source_host_name)

            delete_reason = _shall_cleanup_piggyback_file(piggyback_max_cachefile_age,
                                                          piggyback_file_path, source_host_name,
                                                          keep_sources)
            if delete_reason:
                console.verbose("Removing outdated piggyback file (%s) %s\n" %
                                (delete_reason, piggyback_file_path))
                _remove_piggyback_file(piggyback_file_path)

        # Remove empty backed host directory
        try:
            os.rmdir(backed_host_dir_path)
        except OSError as e:
            if e.errno == errno.ENOTEMPTY:
                pass
            else:
                raise


def _shall_cleanup_piggyback_file(piggyback_max_cachefile_age, piggyback_file_path,
                                  source_host_name, keep_sources):
    # type: (int, str, str, Set[str]) -> Optional[str]
    if source_host_name not in keep_sources:
        return "Source not sending piggyback data"

    try:
        file_age = cmk_base.utils.cachefile_age(piggyback_file_path)
    except MKGeneralException:
        return None  # File might've been deleted. That's ok.

    # Skip piggyback files that are outdated at all
    if file_age > piggyback_max_cachefile_age:
        return "%d seconds too old" % (file_age - piggyback_max_cachefile_age)

    status_file_path = _piggyback_source_status_path(source_host_name)
    if not os.path.exists(status_file_path):
        return "Source not sending piggyback"

    if _is_piggyback_file_outdated(status_file_path, piggyback_file_path):
        return "Not updated by source"

    return None
