#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.store as store

import cmk.gui.gui_background_job


class WatoBackgroundProcess(cmk.gui.gui_background_job.GUIBackgroundProcess):
    def initialize_environment(self):
        super().initialize_environment()
        if self._jobstatus.get_status_from_file().get("lock_wato"):
            store.release_all_locks()
            store.lock_exclusive()


class WatoBackgroundJob(cmk.gui.gui_background_job.GUIBackgroundJob):
    _background_process_class = WatoBackgroundProcess
