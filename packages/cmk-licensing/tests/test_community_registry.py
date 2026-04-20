#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition
from cmk.licensing.community_handler import CommunityLicensingHandler
from cmk.licensing.handler import LicensingHandler
from cmk.licensing.registry import (
    licensing_handler_registry,
    register_community_licensing_handler,
)


def test_licensing_handler_registry_community() -> None:
    register_community_licensing_handler()
    handler = licensing_handler_registry[Edition.COMMUNITY]()
    assert isinstance(handler, CommunityLicensingHandler)
    assert isinstance(handler, LicensingHandler)
