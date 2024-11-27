#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..v0_unstable._registry import QuickSetupRegistry
from .aws.stages import quick_setup_aws
from .azure.stages import quick_setup_azure
from .gcp.stages import quick_setup_gcp


def register(registry: QuickSetupRegistry) -> None:
    registry.register(quick_setup_aws)
    registry.register(quick_setup_azure)
    registry.register(quick_setup_gcp)
