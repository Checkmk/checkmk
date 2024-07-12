#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.quick_setup.definitions import QuickSetupRegistry

from .aws_stages import quick_setup_aws


def register(registry: QuickSetupRegistry) -> None:
    registry.register(quick_setup_aws)
