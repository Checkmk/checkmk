#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _


def notification_macro_help() -> str:
    return _(
        "Here you are allowed to use all macros that are defined in the "
        "notification context.<br>"
        "The most important are:"
        "<ul>"
        "<li><tt>$HOSTNAME$</li>"
        "<li><tt>$SERVICEDESC$</li>"
        "<li><tt>$SERVICESHORTSTATE$</li>"
        "<li><tt>$SERVICEOUTPUT$</li>"
        "<li><tt>$LONGSERVICEOUTPUT$</li>"
        "<li><tt>$SERVICEPERFDATA$</li>"
        "<li><tt>$EVENT_TXT$</li>"
        "</ul>"
    )
