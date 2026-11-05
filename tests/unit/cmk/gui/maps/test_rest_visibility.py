#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.maps.rest_api.utils import visibility_from_public


def test_whom_a_map_is_shared_with_is_shown_to_its_editors() -> None:
    visibility = visibility_from_public(("contact_groups", ["ops"]), False, can_edit=True)
    assert (visibility.publish, visibility.groups) == ("contact_groups", ["ops"])


def test_whom_a_map_is_shared_with_is_not_shown_to_its_viewers() -> None:
    visibility = visibility_from_public(("contact_groups", ["ops"]), False, can_edit=False)
    assert visibility.publish == "contact_groups"
    assert isinstance(visibility.groups, ApiOmitted)
