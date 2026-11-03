#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from cmk.gui.i18n import _


def fake_check_output(*, output: str, metrics: str, state_title: str, author: UserId) -> str:
    """The plug-in output a faked check result carries, built as the legacy command builds it."""
    text = output.strip() or _("Manually set to %(state)s by %(user)s") % {
        "state": state_title,
        "user": author,
    }
    perfdata = metrics.strip()
    return f"{text}|{perfdata}" if perfdata else text
