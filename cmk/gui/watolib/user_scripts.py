#!/usr/bin/python
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
"""Common code for reading and offering notification scripts and alert handlers.

# Example header of a notification script:

#!/usr/bin/python
# HTML Emails with included graphs
# Bulk: yes
# Argument 1: Full system path to the pnp4nagios index.php for fetching the graphs. Usually auto configured in OMD.
# Argument 2: HTTP-URL-Prefix to open Multisite. When provided, several links are added to the mail.
#
# This script creates a nifty HTML email in multipart format with
# attached graphs and such neat stuff. Sweet!
"""

import os
import re

import cmk.utils.paths

from cmk.gui.i18n import _u


def load_user_scripts(what):
    scripts = {}
    not_dir = cmk.utils.paths.share_dir + "/" + what
    try:
        if what == "notifications":
            # Support for setup.sh
            not_dir = cmk.utils.paths.notifications_dir
    except Exception:
        pass

    scripts = _load_user_scripts_from(not_dir)
    try:
        local_dir = cmk.utils.paths.omd_root + "/local/share/check_mk/" + what
        scripts.update(_load_user_scripts_from(local_dir))
    except Exception:
        pass

    return scripts


def _load_user_scripts_from(adir):
    scripts = {}
    if os.path.exists(adir):
        for entry in os.listdir(adir):
            entry = entry.decode("utf-8")
            path = adir + "/" + entry
            if os.path.isfile(path) and os.access(path, os.X_OK):
                info = {"title": entry, "bulk": False}
                try:
                    lines = file(path)
                    next(lines)
                    line = lines.next().decode("utf-8").strip()
                    if line.startswith("#") and re.search(r'coding[=:]\s*([-\w.]+)', line):
                        line = lines.next().strip()
                    if line.startswith("#"):
                        info["title"] = line.lstrip("#").strip().split("#", 1)[0]
                    while True:
                        line = lines.next().strip()
                        if not line.startswith("#") or ":" not in line:
                            break
                        key, value = line[1:].strip().split(":", 1)
                        value = value.strip()
                        if key.lower() == "bulk":
                            info["bulk"] = (value == "yes")

                except Exception:
                    pass
                scripts[entry] = info
    return scripts


def load_notification_scripts():
    return load_user_scripts("notifications")


def user_script_choices(what):
    scripts = load_user_scripts(what)
    choices = [(name, info["title"]) for (name, info) in scripts.items()]
    choices = [(k, _u(v)) for k, v in sorted(choices, key=lambda x: x[1])]
    return choices


def user_script_title(what, name):
    return dict(user_script_choices(what)).get(name, name)
