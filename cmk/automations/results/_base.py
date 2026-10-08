#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Types shared by the concrete result modules.

The result type itself is cmk.automations.internal.AutomationResult.
"""

from cmk.ruleset_matcher.labels import HostLabelValueDict

DiscoveredHostLabelsDict = dict[str, HostLabelValueDict]
