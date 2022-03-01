#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

# This GUI specific fixture is also needed in this context
from tests.unit.cmk.gui.conftest import load_plugins  # noqa: F401 # pylint: disable=unused-import

from cmk.gui.utils.logged_in import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context


@pytest.fixture(autouse=True, name="gui_context")
def fixture_gui_context():
    with gui_context(), SuperUserContext():
        yield
