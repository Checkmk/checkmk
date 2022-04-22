#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _


def remove_tls_registration_help() -> str:
    return _(
        "<br>This action invalidates the stored connection data and the host connections will not"
        " work any longer. There are only 2 reasons to do this:"
        "<ul>"
        "<li>You do not trust this host any longer and don't want to receive or fetch data"
        " anymore.</li>"
        "<li>You want to reset the communication to the legacy and unencrypted mode (in which case"
        " you also need to reset the agent controller on the monitored host (refer to"
        " `cmk-agent-ctl help`).</li>"
        "</ul>"
    )
