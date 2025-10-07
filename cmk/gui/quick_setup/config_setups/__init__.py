#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..v0_unstable._registry import QuickSetupRegistry
from .aws.stages import quick_setup_aws
from .azure_deprecated.stages import quick_setup_azure as quick_setup_azure_deprecated
from .azure_v2.stages import quick_setup_azure as quick_setup_azure_v2
from .gcp.stages import quick_setup_gcp


def register(registry: QuickSetupRegistry) -> None:
    registry.register(quick_setup_aws)
    registry.register(quick_setup_azure_deprecated)
    registry.register(quick_setup_azure_v2)
    registry.register(quick_setup_gcp)
