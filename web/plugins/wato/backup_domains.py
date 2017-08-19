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

import cmk.paths

watolib.backup_domains.update({
    "check_mk": {
      "group"       : _("Configuration"),
      "title"       : _("Hosts, Services, Groups, Timeperiods, Business Intelligence and Monitoring Configuration"),
      "prefix"      : cmk.paths.default_config_dir,
      "paths"       : [
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
      "default"     : True,
    },
    "authorization_v1": {
      "group"       : _("Configuration"),
      "title"       : _("Local Authentication Data"),
      "prefix"      : cmk.paths.omd_root,
      "paths"       : [
                        ("file", "etc/htpasswd"),
                        ("file", "etc/auth.secret"),
                        ("file", "etc/auth.serials"),
                        ("file", "var/check_mk/web/*/serial.mk"),
                        ("file", "var/check_mk/web/*/automation.secret"),
                      ],
      "cleanup"     : False,
      "default"     : True
    },
    "mkeventstatus": {
      "group"       : _("Configuration"),
      "title"       : _("Event Console Configuration"),
      "prefix"      : cmk.paths.omd_root,
      "paths"       : [
                        ("dir",  "etc/check_mk/mkeventd.d"),
                      ],
      "default"     : True
    },
    "extensions" : {
        "title"    : _("Extensions in <tt>~/local/</tt> and MKPs"),
        "prefix"   : cmk.paths.omd_root,
        "paths"    : [
                        ("dir", "var/check_mk/packages" ),
                        ("dir", "local" ),
                     ],
        "default"  : True,
    },
})
