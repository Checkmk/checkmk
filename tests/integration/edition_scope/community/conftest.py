#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui import main_modules


@pytest.fixture(scope="session")
def load_gui_plugins() -> None:
    """Run the gui edition's full plug-in registration chain

    Populates the GUI registries with the production set of this edition, which is what the
    snapshots in this directory assert on.
    """
    main_modules.register(Edition.COMMUNITY)

    if errors := main_modules.get_failed_plugins():
        raise Exception(f"The following errors occurred during plug-in loading: {errors}")
