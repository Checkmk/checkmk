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

import os

import cmk.paths
import cmk.translations
import cmk.store as store
from cmk.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config


def get_piggyback_raw_data(hostname):
    output = ""
    if not hostname:
        return output

    for sourcehost, file_path in _get_piggyback_files(hostname):
        console.verbose("Using piggyback raw data from host %s.\n" % sourcehost)
        output += file(file_path).read()

    return output


def has_piggyback_raw_data(hostname):
    return _get_piggyback_files(hostname) != []


def _get_piggyback_files(hostname):
    """Gather a list of piggyback files to read for further processing.

    Please note that there may be multiple parallel calls executing the
    _get_piggyback_files(), store_piggyback_raw_data() or cleanup_piggyback_files()
    functions. Therefor all these functions needs to deal with suddenly vanishing or
    updated files/directories.
    """
    files = []
    piggyback_dir = os.path.join(cmk.paths.tmp_dir, "piggyback", hostname)

    # cleanup_piggyback_files() may remove stale piggyback files of one source
    # host and also the directory "hostname" when the last piggyback file for the
    # current host was removed. This may cause the os.listdir() to fail. We treat
    # this as regular case: No piggyback files for the current host.
    try:
        source_host_names = os.listdir(piggyback_dir)
    except OSError, e:
        if e.errno == 2: # No such file or directory
            return files
        else:
            raise

    for sourcehost in source_host_names:
        if sourcehost.startswith("."):
            continue

        file_path = os.path.join(piggyback_dir, sourcehost)

        try:
            file_age = cmk_base.utils.cachefile_age(file_path)
        except MKGeneralException, e:
            continue # File might've been deleted. That's ok.

        # Skip piggyback files that are outdated at all
        if file_age > config.piggyback_max_cachefile_age:
            console.verbose("Piggyback file %s is outdated (%d seconds too old). Skip processing.\n" %
                (file_path, file_age - config.piggyback_max_cachefile_age))
            continue

        # Skip piggyback files that have not been updated in the last contact
        # with the source host that is currently being handled.
        try:
            source_update_age = _piggyback_source_host_update_age(sourcehost)
        except MKGeneralException, e:
            console.verbose("Piggyback file %s is outdated (Source not sending piggyback). Skip processing.\n" % file_path)
            continue # No source_status_file exists -> ignore data from this source

        if file_age > source_update_age:
            console.verbose("Piggyback file %s is outdated (Not updated by source). Skip processing.\n" % file_path)
            continue

        files.append((sourcehost, file_path))

    return files


def _piggyback_source_status_path(sourcehost):
    return os.path.join(cmk.paths.tmp_dir, "piggyback_sources", sourcehost)


def _piggyback_source_host_update_age(sourcehost):
    return cmk_base.utils.cachefile_age(_piggyback_source_status_path(sourcehost))


def _remove_piggyback_file(file_path):
    try:
        os.remove(file_path)
        return True
    except OSError, e:
        if e.errno == 2: # No such file or directory
            return False
        else:
            raise


def remove_source_status_file(sourcehost):
    """Remove the source_status_file of this piggyback host which will
    mark the piggyback data from this source as outdated."""
    source_status_path = _piggyback_source_status_path(sourcehost)
    return _remove_piggyback_file(source_status_path)


def store_piggyback_raw_data(sourcehost, piggybacked_raw_data):
    for backedhost, lines in piggybacked_raw_data.items():
        console.verbose("Storing piggyback data for: %s\n" % backedhost)
        content = "\n".join(lines) + "\n"
        store.save_file(os.path.join(cmk.paths.tmp_dir, "piggyback", backedhost, sourcehost), content)

    # Store the last contact with this piggyback source to be able to filter outdated data later
    # We use the mtime of this file later for comparision.
    # Only do this for hosts that sent piggyback data this turn, cleanup the status file when no
    # piggyback data was sent this turn.
    if piggybacked_raw_data:
        store.save_file(_piggyback_source_status_path(sourcehost), "")
    else:
        remove_source_status_file(sourcehost)


def cleanup_piggyback_files():
    """This is a housekeeping job to clean up different old files from the
    piggyback directories.

    # Cleanup piggyback data of hosts that are not sending piggyback data anymore
    # a) hosts that have a file below piggyback_sources:
    #    -> check age of the file and remove it once it reached config.piggyback_max_cachefile_age
    # b) hosts that don't have a file below piggyback_sources (old version or removed by step "a)"):
    #    -> remove all piggyback_raw_data files created by this source

    # Cleanup empty backed host directories below "piggyback"

    Please note that there may be multiple parallel calls executing the
    _get_piggyback_files(), store_piggyback_raw_data() or cleanup_piggyback_files()
    functions. Therefor all these functions needs to deal with suddenly vanishing or
    updated files/directories.
    """
    _cleanup_old_source_status_files()
    _cleanup_old_piggybacked_files()


def _cleanup_old_source_status_files():
    base_dir = os.path.join(cmk.paths.tmp_dir, "piggyback_sources")
    for entry in os.listdir(base_dir):
        if entry[0] == ".":
            continue

        file_path = os.path.join(base_dir, entry)

        try:
            file_age = cmk_base.utils.cachefile_age(file_path)
        except MKGeneralException, e:
            continue # File might've been deleted. That's ok.

        if file_age > config.piggyback_max_cachefile_age:
            console.verbose("Removing outdated piggyback source status file %s\n" % file_path)
            _remove_piggyback_file(file_path)

def _cleanup_old_piggybacked_files():
    """Remove piggyback data that is not needed anymore

    The monitoring (_get_piggyback_files()) is already skipping these files,
    but we need some cleanup mechanism.

    - Remove all piggyback files created by sources without status file
    - Remove all piggyback files that are older that the current status file of the source host
    - Cleanup empty backed host directories below "piggyback"
    """
    keep_sources = set(os.listdir(os.path.join(cmk.paths.tmp_dir, "piggyback_sources")))

    base_dir = os.path.join(cmk.paths.tmp_dir, "piggyback")
    for backed_host_name in os.listdir(base_dir):
        if backed_host_name[0] == ".":
            continue

        # Cleanup piggyback files from sources that we have no status file for
        backed_host_dir_path = os.path.join(base_dir, backed_host_name)
        for source_host_name in os.listdir(backed_host_dir_path):
            if source_host_name[0] == ".":
                continue

            file_path = os.path.join(backed_host_dir_path, source_host_name)

            delete_reason = _shall_cleanup_piggyback_file(file_path, source_host_name, keep_sources)
            if delete_reason:
                console.verbose("Removing outdated piggyback file (%s) %s\n" % (delete_reason, file_path))
                _remove_piggyback_file(file_path)

        # Remove empty backed host directory
        try:
            os.rmdir(backed_host_dir_path)
        except OSError, e:
            if e.errno == 39: #Directory not empty
                pass
            else:
                raise


def _shall_cleanup_piggyback_file(file_path, source_host_name, keep_sources):
    if source_host_name not in keep_sources:
        return "Source not sending piggyback data"

    try:
        file_age = cmk_base.utils.cachefile_age(file_path)
    except MKGeneralException, e:
        return None # File might've been deleted. That's ok.

    # Skip piggyback files that are outdated at all
    if file_age > config.piggyback_max_cachefile_age:
        return "%d seconds too old" % (file_age - config.piggyback_max_cachefile_age)

    # Skip piggyback files that have not been updated in the last contact
    # with the source host that is currently being handled.
    try:
        source_update_age = _piggyback_source_host_update_age(source_host_name)
    except MKGeneralException, e:
        return "Source not sending piggyback"

    if file_age > source_update_age:
        return "Not updated by source"

    return None
