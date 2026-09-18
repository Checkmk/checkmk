#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

r"""
Scope
-----

This API provides functionality to create licensing plug-ins that can be
discovered by Checkmk. Such plug-ins let a feature contribute its licensing
aspects -- currently its usage counters -- without the licensing engine
naming the feature.

To be discovered, a plug-in module must be placed in the ``licensing``
subdirectory of a plug-in family (e.g.
``cmk/plugins/<family>/licensing/<module>.py``) and the plug-in instance name
must start with the corresponding prefix.
"""

from collections.abc import Mapping

from ._counters import (
    CounterCollectionContext as CounterCollectionContext,
)
from ._counters import (
    LICENSE_LABEL_EXCLUDE as LICENSE_LABEL_EXCLUDE,
)
from ._counters import (
    LICENSE_LABEL_NAME as LICENSE_LABEL_NAME,
)
from ._counters import (
    LicenseUsageCounter as LicenseUsageCounter,
)
from ._counters import (
    LicenseUsageCounterName as LicenseUsageCounterName,
)


def entry_point_prefixes() -> Mapping[type[LicenseUsageCounter], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    license_usage_counter_... = LicenseUsageCounter(...)
    """
    return {
        LicenseUsageCounter: "license_usage_counter_",
    }
