#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The gates a request passes before it reaches Setup."""

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.config import Config
from cmk.gui.customer import is_provider_site
from cmk.gui.i18n import _


def ensure_setup_enabled(config: Config) -> None:
    if not config.wato_enabled:
        raise MKGeneralException(
            _(
                "Setup is disabled. Please set <tt>wato_enabled = True</tt>"
                " in your <tt>multisite.mk</tt> if you want to use Setup."
            )
        )


def ensure_provider_site(config: Config) -> None:
    if not is_provider_site(config):
        raise MKGeneralException(_("Checkmk can only be configured on the managers central site."))
