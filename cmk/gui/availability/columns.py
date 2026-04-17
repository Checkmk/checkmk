#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

from collections.abc import Sequence

from cmk.gui.i18n import _

from .type_defs import _ColumnSpec, AVObjectType


class AvailabilityColumns:
    def __init__(self) -> None:
        super().__init__()
        self.host = self._host_availability_columns()
        self.service = self._service_availability_columns()
        self.bi = self._bi_availability_columns()

    # TODO: Nuke this abomination!
    def __getitem__(self, key: AVObjectType) -> Sequence[_ColumnSpec]:
        return getattr(self, key)

    def _host_availability_columns(self) -> Sequence[_ColumnSpec]:
        return [
            ("up", "state0", _("UP"), None),
            ("down", "state2", _("DOWN"), None),
            ("unreach", "state3", _("UNREACH"), None),
            ("flapping", "flapping", _("Flapping"), None),
            ("in_downtime", "downtime", _("Downtime"), _("The host was in a scheduled downtime")),
            ("outof_notification_period", "", _("OO/Notif"), _("Out of Notification Period")),
            ("outof_service_period", "ooservice", _("OO/Service"), _("Out of service period")),
            (
                "unmonitored",
                "unmonitored",
                _("N/A"),
                _("During this time period no monitoring data is available"),
            ),
        ]

    def _service_availability_columns(self) -> Sequence[_ColumnSpec]:
        return [
            ("ok", "state0", _("OK"), None),
            ("warn", "state1", _("WARN"), None),
            ("crit", "state2", _("CRIT"), None),
            ("unknown", "state3", _("UNKNOWN"), None),
            ("flapping", "flapping", _("Flapping"), None),
            ("host_down", "hostdown", _("H.Down"), _("The host was down")),
            (
                "in_downtime",
                "downtime",
                _("Downtime"),
                _("The host or service was in a scheduled downtime"),
            ),
            ("outof_notification_period", "", _("OO/Notif"), _("Out of Notification Period")),
            ("outof_service_period", "ooservice", _("OO/Service"), _("Out of service period")),
            (
                "unmonitored",
                "unmonitored",
                _("N/A"),
                _("During this time period no monitoring data is available"),
            ),
        ]

    def _bi_availability_columns(self) -> Sequence[_ColumnSpec]:
        return [
            ("ok", "state0", _("OK"), None),
            ("warn", "state1", _("WARN"), None),
            ("crit", "state2", _("CRIT"), None),
            ("unknown", "state3", _("UNKNOWN"), None),
            (
                "in_downtime",
                "downtime",
                _("Downtime"),
                _("The aggregate was in a scheduled downtime"),
            ),
            (
                "unmonitored",
                "unmonitored",
                _("N/A"),
                _("During this time period no monitoring data is available"),
            ),
        ]
