#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_livestatus_status = translations.Translation(
    name="livestatus_status",
    check_commands=[translations.PassiveCheck("livestatus_status")],
    translations={
        "connections": translations.RenameTo("livestatus_connect_rate"),
        "host_checks": translations.RenameTo("host_check_rate"),
        "log_messages": translations.RenameTo("log_message_rate"),
        "requests": translations.RenameTo("livestatus_request_rate"),
        "service_checks": translations.RenameTo("service_check_rate"),
        "site_cert_days": translations.ScaleBy(24 * 60 * 60),
    },
)
