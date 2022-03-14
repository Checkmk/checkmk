#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Common code for reading and offering notification scripts and alert handlers.

# Example header of a notification script:

#!/usr/bin/env python3
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
from pathlib import Path

from six import ensure_str

import cmk.utils.paths

from cmk.gui.i18n import _u
from cmk.gui.permissions import declare_permission


def load_user_scripts(what):
    scripts = {}
    not_dir = cmk.utils.paths.share_dir + "/" + what
    try:
        if what == "notifications":
            # Support for setup.sh
            not_dir = str(cmk.utils.paths.notifications_dir)
    except Exception:
        pass

    scripts = _load_user_scripts_from(not_dir)
    try:
        local_dir = str(cmk.utils.paths.omd_root / "local/share/check_mk" / what)
        scripts.update(_load_user_scripts_from(local_dir))
    except Exception:
        pass

    return scripts


def _load_user_scripts_from(adir):
    scripts = {}
    if os.path.exists(adir):
        for entry in os.listdir(adir):
            entry = ensure_str(entry)  # pylint: disable= six-ensure-str-bin-call
            if entry == ".f12":
                continue
            path = adir + "/" + entry
            if os.path.isfile(path) and os.access(path, os.X_OK):
                info = {"title": entry, "bulk": False}
                try:
                    with Path(path).open(encoding="utf-8") as lines:
                        next(lines)
                        line = next(lines).strip()
                        if line.startswith("#") and re.search(r"coding[=:]\s*([-\w.]+)", line):
                            line = next(lines).strip()
                        if line.startswith("#"):
                            info["title"] = line.lstrip("#").strip().split("#", 1)[0]
                        while True:
                            line = next(lines).strip()
                            if not line.startswith("#") or ":" not in line:
                                break
                            key, value = line[1:].strip().split(":", 1)
                            value = value.strip()
                            if key.lower() == "bulk":
                                info["bulk"] = value == "yes"

                except Exception:
                    pass
                scripts[entry] = info
    return scripts


def load_notification_scripts():
    return load_user_scripts("notifications")


# The permissions need to be loaded dynamically instead of only when the plugins are loaded because
# the user may have placed new notification plugins in the local hierarchy.
def declare_notification_plugin_permissions() -> None:
    for name, attrs in load_notification_scripts().items():
        if name[0] == ".":
            continue

        declare_permission(
            "notification_plugin.%s" % name, _u(attrs["title"]), "", ["admin", "user"]
        )


def user_script_choices(what):
    scripts = load_user_scripts(what)
    choices = [(name, info["title"]) for (name, info) in scripts.items()]
    choices = [(k, _u(v)) for k, v in sorted(choices, key=lambda x: x[1])]
    return choices


def user_script_title(what, name):
    return dict(user_script_choices(what)).get(name, name)
