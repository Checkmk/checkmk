#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import UserId

from cmk.gui.type_defs import Visual

from cmk.update_config.plugins.actions.visuals_utils import _set_packaged_key


def test_set_packaged_key() -> None:
    view_spec: Visual = Visual(
        owner="dummy_user",
        name="test_visual",
        context={},
        single_infos=[],
        add_context_to_title=False,
        title="Test visual",
        description="Desc",
        topic="Topic",
        sort_index=10,
        is_show_more=False,
        icon="test_icon",
        hidden=False,
        hidebutton=False,
        public=False,
        link_from={},
    )  # type: ignore[typeddict-item]

    _set_packaged_key({(UserId("dummy_user"), "visual_name"): view_spec})

    assert view_spec["packaged"] is False
