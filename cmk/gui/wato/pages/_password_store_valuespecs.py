#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.watolib.password_store import (
    IndividualOrStoredPassword as IndividualOrStoredPassword,
)
from cmk.gui.watolib.password_store import (
    MigrateNotUpdatedToIndividualOrStoredPassword as MigrateNotUpdatedToIndividualOrStoredPassword,
)
from cmk.gui.watolib.password_store import (
    MigrateToIndividualOrStoredPassword as MigrateToIndividualOrStoredPassword,
)

PasswordFromStore = IndividualOrStoredPassword  # CMK-12228
