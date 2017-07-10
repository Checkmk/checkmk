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
import cmk.hostname_translation
import cmk.store as store
from cmk.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config


def get_piggyback_info(hostname):
    output = ""
    if not hostname:
        return output
    for sourcehost, file_path in get_piggyback_files(hostname):
        console.verbose("Using piggyback information from host %s.\n" % sourcehost)
        output += file(file_path).read()
    return output


def has_piggyback_info(hostname):
    return get_piggyback_files(hostname) != []


def get_piggyback_files(hostname):
    files = []
    dir = cmk.paths.tmp_dir + "/piggyback/" + hostname

    # remove_piggyback_info_from() may remove stale piggyback files of one source
    # host and also the directory "hostname" when the last piggyback file for the
    # current host was removed. This may cause the os.listdir() to fail. We treat
    # this as regular case: No piggyback files for the current host.
    try:
        source_hosts = os.listdir(dir)
    except OSError, e:
        if e.errno == 2: # No such file or directory
            return files
        else:
            raise

    for sourcehost in source_hosts:
        if sourcehost.startswith("."):
            continue

        file_path = dir + "/" + sourcehost

        try:
            file_age = cmk_base.utils.cachefile_age(file_path)
        except MKGeneralException, e:
            continue # File might've been deleted. That's ok.

        # Cleanup outdated files
        if file_age > config.piggyback_max_cachefile_age:
            console.verbose("Piggyback file %s is outdated by %d seconds. Deleting it.\n" %
                (file_path, file_age - config.piggyback_max_cachefile_age))

            try:
                os.remove(file_path)
            except OSError, e:
                if e.errno == 2: # No such file or directory
                    pass # Deleted in the meantime. That's ok.
                else:
                    raise

            continue

        files.append((sourcehost, file_path))

    return files


def store_piggyback_info(sourcehost, piggybacked):
    for backedhost, lines in piggybacked.items():
        console.verbose("Storing piggyback data for %s.\n" % backedhost)
        content = "\n".join(lines) + "\n"
        store.save_file(os.path.join(cmk.paths.tmp_dir, "piggyback", backedhost, sourcehost), content)

    # Remove piggybacked information that is not
    # being sent this turn
    remove_piggyback_info_from(sourcehost, keep=piggybacked.keys())


def remove_piggyback_info_from(sourcehost, keep=None):
    if keep is None:
        keep = []

    removed = 0
    piggyback_path = cmk.paths.tmp_dir + "/piggyback/"
    if not os.path.exists(piggyback_path):
        return # Nothing to do

    for backedhost in os.listdir(piggyback_path):
        if backedhost not in ['.', '..'] and backedhost not in keep:
            path = piggyback_path + backedhost + "/" + sourcehost
            if os.path.exists(path):
                console.verbose("Removing stale piggyback file %s\n" % path)
                os.remove(path)
                removed += 1

            # Remove directory if empty
            try:
                os.rmdir(piggyback_path + backedhost)
            except:
                pass
    return removed


def translate_piggyback_host(sourcehost, backedhost):
    translation = config.get_piggyback_translation(sourcehost)

    # To make it possible to match umlauts we need to change the hostname
    # to a unicode string which can then be matched with regexes etc.
    # We assume the incoming name is correctly encoded in UTF-8
    backedhost = config.decode_incoming_string(backedhost)

    translated = cmk.hostname_translation.translate(translation, backedhost)

    return translated.encode('utf-8') # change back to UTF-8 encoded string
