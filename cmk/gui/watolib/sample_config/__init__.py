#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Create an initial Checkmk configuration for new sites"""

from ._constants import PS_DISCOVERY_RULES
from ._impl import (
    ConfigGeneratorAcknowledgeInitialWerks,
    ConfigGeneratorBasicWATOConfig,
    ConfigGeneratorRegistrationUser,
    get_default_notification_rule,
    init_wato_datastructures,
    new_notification_parameter_id,
    new_notification_rule_id,
)

__all__ = [
    "ConfigGeneratorAcknowledgeInitialWerks",
    "ConfigGeneratorBasicWATOConfig",
    "ConfigGeneratorRegistrationUser",
    "new_notification_parameter_id",
    "new_notification_rule_id",
    "get_default_notification_rule",
    "init_wato_datastructures",
    "PS_DISCOVERY_RULES",
]
