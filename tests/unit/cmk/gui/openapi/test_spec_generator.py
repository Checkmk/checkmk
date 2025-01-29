#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import get_args

from cmk.gui.openapi.restful_objects.type_defs import TagGroup
from cmk.gui.openapi.spec import spec_generator


def test_redoc_spec_tag_group_completness() -> None:
    """
    If you add a new TagGroup it also has to be added to the redoc spec definition. Forgetting that
    will break our redoc docu. This test ensures they align.

    The implementation is not ideal. If you find a better way please delete this test
    """
    spec = spec_generator._redoc_spec()
    spec_tag_groups = {el["name"] for el in spec["x-tagGroups"]}
    assert spec_tag_groups == set(get_args(TagGroup))
