#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.statename import core_state_names

from cmk.gui import fields as gui_fields

from cmk import fields


class StateField(fields.String):
    def __init__(self, required: bool):
        super().__init__(
            enum=[v.lower() for v in core_state_names().values() if v != "NODATA"],
            example="ok",
            description="The state",
            required=required,
        )


class PhaseField(fields.String):
    def __init__(self, required: bool):
        super().__init__(
            enum=["open", "ack"],
            example="open",
            description="The event phase, open or ack",
            required=required,
        )


class EventIDField(fields.String):
    def __init__(self, required: bool):
        super().__init__(
            description="The event console event ID.",
            example="1",
            pattern="^[0-9]+$",
            required=required,
        )


class HostNameField(gui_fields.HostField):
    def __init__(self, required: bool):
        super().__init__(
            description="The host name. No exception is raised when the specified host name does not exist",
            should_exist=None,
            example="host_1",
            required=required,
        )


class ApplicationField(fields.String):
    def __init__(self, required: bool):
        super().__init__(
            description="Show events that originated from this app.",
            example="app_1",
            required=required,
        )
