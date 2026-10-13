#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.core_client import CoreAction as CoreAction

from ._control import (
    build_and_activate_monitoring_config as build_and_activate_monitoring_config,
)
from ._control import do_create_config as do_create_config
