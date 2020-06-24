# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import cmk.gui.config as config
import livestatus


class DowntimeSchedule:
    def __init__(self, start_time, end_time, duration, delayed_duration=None, comment=None):
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        if delayed_duration is None:
            delayed_duration = 0
        self.delayed_duration = delayed_duration
        self.comment = comment

    def livestatus_command(self, specification, cmdtag):
        return ("SCHEDULE_" + cmdtag + "_DOWNTIME;%s;" % specification) + ("%d;%d;%d;0;%d;%s;" % (
            self.start_time,
            self.end_time,
            self.duration,
            self.delayed_duration,
            config.user.id,
        )) + livestatus.lqencode(self.comment)
