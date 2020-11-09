#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.version as cmk_version
import cmk.gui.cron as cron


def test_registered_jobs():

    expected = [
        'cmk.gui.inventory.run',
        'cmk.gui.plugins.cron.gui_background_job.housekeeping',
        'cmk.gui.plugins.cron.wato_folder_lookup_cache.rebuild_folder_lookup_cache',
        'cmk.gui.userdb.execute_userdb_job',
        'cmk.gui.wato.execute_network_scan_job',
        'cmk.gui.watolib.activate_changes.execute_activation_cleanup_background_job',
    ]

    if not cmk_version.is_raw_edition():
        expected += [
            'cmk.gui.cee.reporting.cleanup_stored_reports',
            'cmk.gui.cee.reporting.do_scheduled_reports',
        ]

    found_jobs = sorted(["%s.%s" % (f.__module__, f.__name__) for f in cron.multisite_cronjobs])
    assert found_jobs == sorted(expected)
