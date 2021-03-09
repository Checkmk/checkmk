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

import time
from pathlib2 import Path
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.plugins.cron import register_job


def rebuild_folder_lookup_cache():
    """Rebuild folder lookup cache around ~5AM
       This needs to be done, since the cachefile might include outdated/vanished hosts"""

    localtime = time.localtime()
    if not (localtime.tm_hour == 5 and localtime.tm_min < 5):
        return

    cache_path = Path(Folder.host_lookup_cache_path())
    if cache_path.exists() and time.time() - cache_path.stat().st_mtime < 300:
        return

    # Touch the file. The cronjob interval might be faster than the file creation
    # Note: If this takes longer than the RequestTimeout -> Problem
    #       On very big configurations, e.g. 300MB this might take 30-50 seconds
    cache_path.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
    cache_path.touch()
    Folder.build_host_lookup_cache(str(cache_path))


register_job(rebuild_folder_lookup_cache)
