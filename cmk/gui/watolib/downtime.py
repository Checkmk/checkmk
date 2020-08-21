#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time

import cmk.gui.config as config
import cmk.gui.sites as sites
from livestatus import SiteId
import livestatus


def execute_livestatus_command(command, site):
    sites.live().command("[%d] %s" % (int(time.time()), command), SiteId(site))


def remove_downtime_command(cmdtag, downtime_id):
    return "DEL_%s_DOWNTIME;%s" % (cmdtag, downtime_id)


def determine_downtime_mode(recurring_number, delayed_duration):
    """Determining the downtime mode

    The mode is represented by an integer (bit masking?) which contains information
    about the recurring option
    """
    fixed_downtime = 0 if delayed_duration else 1

    if recurring_number:
        mode = recurring_number * 2 + fixed_downtime
    else:
        mode = fixed_downtime

    return mode


class DowntimeSchedule:
    def __init__(self, start_time, end_time, mode, delayed_duration=None, comment=None):
        self.start_time = start_time
        self.end_time = end_time
        self.mode = mode
        if delayed_duration is None:
            delayed_duration = 0
        self.delayed_duration = delayed_duration
        self.comment = comment

    def livestatus_command(self, specification, cmdtag):
        return ("SCHEDULE_" + cmdtag + "_DOWNTIME;%s;" % specification) + ("%d;%d;%d;0;%d;%s;" % (
            self.start_time,
            self.end_time,
            self.mode,
            self.delayed_duration,
            config.user.id,
        )) + livestatus.lqencode(self.comment)
