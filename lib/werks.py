#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

"""Code for processing Check_MK werks. This is needed by several components,
so it's best place is in the central library."""

import os
import json

import cmk.paths
import cmk.store as store

from .exceptions import MKGeneralException

# TODO: Clean this up one day by using the way recommended by gettext.
# (See https://docs.python.org/2/library/gettext.html). For this we
# need the path to the locale files here.
try:
    _
except NameError:
    _ = lambda x: x # Fake i18n when not available


def _compiled_werks_dir():
    return cmk.paths.share_dir + "/werks"


def load():
    werks = {}

    for file_name in os.listdir(_compiled_werks_dir()):
        if file_name != "werks" and not file_name.startswith("werks-"):
            continue

        path = os.path.join(_compiled_werks_dir(), file_name)
        for werk_id, werk in json.load(open(path)).items():
            werks[int(werk_id)] = werk

    return werks


def load_raw_files(werks_dir):
    werks = {}

    if werks_dir is None:
        werks_dir = cmk.paths.share_dir + "/werks"

    try:
        for file_name in os.listdir(werks_dir):
            if file_name[0].isdigit():
                werk_id = int(file_name)
                try:
                    werk = _load_werk(os.path.join(werks_dir, file_name))
                    werk["id"] = werk_id
                    werks[werk_id] = werk
                except Exception, e:
                    raise MKGeneralException(_("Failed to load werk \"%s\": %s") % (werk_id, e))
    except OSError, e:
        if e.errno == 2:
            pass # werk directory not existing
        else:
            raise

    return werks


def _load_werk(path):
    werk = {
        "body" : [],
    }
    in_header = True
    for line in file(path):
        line = line.strip().decode("utf-8")
        if in_header and not line:
            in_header = False
        elif in_header:
            key, text = line.split(":", 1)
            try:
                value = int(text.strip())
            except ValueError:
                value = text.strip()
            werk[key.lower()] = value
        else:
            werk["body"].append(line)
    if "compatible" not in werk: # missing in some legacy werks
        werk["compatible"] = "compat"
    return werk


def write_precompiled_werks(path, werks):
    with open(path, "w") as f:
        json.dump(werks, f, check_circular=False)
    #store.save_data_to_file(path, werks, pretty=False)
