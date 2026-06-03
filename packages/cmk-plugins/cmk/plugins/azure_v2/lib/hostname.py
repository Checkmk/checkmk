#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unique host name computation for Azure entities.

This module must stay stdlib-only (see package docstring).
"""

import hashlib
from collections.abc import Sequence

_HASH_CHARS_TO_KEEP = 8


def compute_unique_name_hash(uniqueness_keys: Sequence[str]) -> str:
    """
    Keys for the hash:
    Tenant: no need to add anything, since the tenant should be unique (and the tenant is
    the "main" host in checkmk, so the user-defined-name)

    Subscription:   subscription-id
    Resource-group: subscription-id,  (it is not possibile to create two resource-groups with the same name in the same subscription)
                    resource-type (a resource-group can have the same name of a subscription)
    Resource:   subscription-id,
                resource-group (lower, because azure do not ensure returning a consistent casing),
                resource-type (not lower, wecause we have seen types with different casing)
    """
    unique_string = f"azure{''.join(uniqueness_keys)}"
    hashed = hashlib.sha256(unique_string.encode("utf-8"), usedforsecurity=False).hexdigest()[
        -_HASH_CHARS_TO_KEEP:
    ]
    return hashed
