#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import get_args

from cmk.gui.openapi.api_endpoints.audit_log.list_audit_log import AuditLogObjectType
from cmk.gui.watolib.objref import ObjectRefType


def test_audit_log_object_type_filter_stays_in_sync_with_object_ref_type() -> None:
    """AuditLogObjectType is hand-written (see list_audit_log.py for why), so guard against it
    silently drifting out of sync whenever ObjectRefType gains or loses a member."""
    ref_type_names = {member.name for member in ObjectRefType}
    filter_values = set(get_args(AuditLogObjectType))

    assert filter_values - {"All", "None"} == ref_type_names
