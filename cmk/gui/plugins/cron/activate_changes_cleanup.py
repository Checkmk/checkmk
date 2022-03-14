#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.cron import register_job
from cmk.gui.watolib.activate_changes import execute_activation_cleanup_background_job

register_job(execute_activation_cleanup_background_job)
