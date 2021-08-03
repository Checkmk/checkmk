#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.utils.logged_in import SuperUserContext
from cmk.gui.utils.script_helpers import application_and_request_context, initialize_gui_environment


@pytest.fixture(autouse=True)
def gui_context():
    with application_and_request_context(), SuperUserContext():
        initialize_gui_environment()
        yield
