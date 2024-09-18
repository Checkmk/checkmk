#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.quick_setup.v0_unstable.predefined._complete as complete
import cmk.gui.quick_setup.v0_unstable.predefined._recaps as recaps
import cmk.gui.quick_setup.v0_unstable.predefined._validators as validators
import cmk.gui.quick_setup.v0_unstable.predefined._widgets as widgets
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_params_from_form_data as collect_params_from_form_data,
)
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_params_with_defaults_from_form_data as collect_params_with_defaults_from_form_data,
)
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_passwords_from_form_data as collect_passwords_from_form_data,
)
from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    build_quick_setup_formspec_map as build_quick_setup_formspec_map,
)
from cmk.gui.quick_setup.v0_unstable.predefined._common import stage_components as stage_components

__all__ = [
    "complete",
    "recaps",
    "validators",
    "widgets",
    "collect_params_from_form_data",
    "build_quick_setup_formspec_map",
    "stage_components",
    "collect_params_with_defaults_from_form_data",
    "collect_passwords_from_form_data",
]
