#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths

from cmk.gui.i18n import _
from cmk.gui.watolib.snapshots import backup_domains

backup_domains.update(
    {
        "check_mk": {
            "group": _("Configuration"),
            "title": _(
                "Hosts, Services, Groups, Timeperiods, Business Intelligence and Monitoring Configuration"
            ),
            "prefix": cmk.utils.paths.default_config_dir,
            "paths": [
                ("file", "liveproxyd.mk"),
                ("file", "main.mk"),
                ("file", "final.mk"),
                ("file", "local.mk"),
                ("file", "mkeventd.mk"),
                ("file", "backup.mk"),
                ("dir", "conf.d"),
                ("dir", "multisite.d"),
                ("dir", "mkeventd.d"),
                ("dir", "mknotifyd.d"),
            ],
            "default": True,
        },
        "authorization_v1": {
            "group": _("Configuration"),
            "title": _("Local Authentication Data"),
            "prefix": cmk.utils.paths.omd_root,
            "paths": [
                ("file", "etc/htpasswd"),
                ("file", "etc/auth.secret"),
                ("file", "etc/auth.serials"),
                ("file", "var/check_mk/web/*/serial.mk"),
                ("file", "var/check_mk/web/*/automation.secret"),
            ],
            "cleanup": False,
            "default": True,
        },
        "mkeventstatus": {
            "group": _("Configuration"),
            "title": _("Event Console Configuration"),
            "prefix": cmk.utils.paths.omd_root,
            "paths": [
                ("dir", "etc/check_mk/mkeventd.d"),
            ],
            "default": True,
        },
        "extensions": {
            "title": _("Extensions in <tt>~/local/</tt> and MKPs"),
            "prefix": cmk.utils.paths.omd_root,
            "paths": [
                ("dir", "var/check_mk/packages"),
                ("dir", "local"),
            ],
        },
    }
)
