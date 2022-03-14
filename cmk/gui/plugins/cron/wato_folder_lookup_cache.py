#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

from cmk.gui.cron import register_job
from cmk.gui.watolib.hosts_and_folders import Folder


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
