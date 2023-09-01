#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.utils import IndividualOrStoredPassword
from cmk.gui.valuespec import MigrateNotUpdated, ValueSpecHelp


def MigrateNotUpdatedToIndividualOrStoredPassword(  # pylint: disable=redefined-builtin
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
) -> MigrateNotUpdated:
    return MigrateNotUpdated(
        valuespec=IndividualOrStoredPassword(
            title=title,
            help=help,
            allow_empty=allow_empty,
            size=size,
        ),
        migrate=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )
