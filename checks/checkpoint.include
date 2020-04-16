#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def scan_checkpoint(oid):
    # we must keep this function with the current name, as long as
    # not all checkpoint check plugins are migrated.
    # see cmk.base.plugins.agent_based.utils.checkpoint.DETECT
    raise NotImplementedError("already migrated")


checkpoint_sensorstatus_to_nagios = {
    "0": (0, "sensor in range"),
    "1": (2, "sensor out of range"),
    "2": (3, "reading error"),
}
