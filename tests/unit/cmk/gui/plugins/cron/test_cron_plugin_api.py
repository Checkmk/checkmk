#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.cron
import cmk.gui.plugins.cron


def test_pre_21_plugin_api_names() -> None:
    for name in (
        "multisite_cronjobs",
        "register_job",
    ):
        assert name in cmk.gui.plugins.cron.__dict__


def test_plugin_api_names() -> None:
    assert "register_job" in cmk.gui.cron.__dict__
