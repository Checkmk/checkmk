#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import Visual
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.visuals import available_by_owner

ALPHA = UserId("alpha")
BETA = UserId("beta")


def _published_visual(owner: UserId, name: str) -> Visual:
    return Visual(
        owner=owner,
        name=name,
        context={},
        single_infos=[],
        add_context_to_title=False,
        title=f"View of {owner}",
        description="",
        topic="my_workplace",
        sort_index=99,
        is_show_more=False,
        icon=None,
        hidden=False,
        hidebutton=False,
        public=True,
        packaged=False,
        link_from={},
        main_menu_search_terms=[],
    )


@pytest.mark.usefixtures("with_user_login")
@pytest.mark.parametrize(
    "owners",
    [
        pytest.param([ALPHA, BETA], id="alphabetically ordered owners"),
        pytest.param([BETA, ALPHA], id="reversely ordered owners"),
    ],
)
def test_available_by_owner_is_independent_of_owner_order(
    owners: Sequence[UserId], load_config: Config
) -> None:
    all_visuals = {
        (owner, "shared_view"): _published_visual(owner, "shared_view") for owner in owners
    }

    assert available_by_owner(
        "views",
        all_visuals,
        UserPermissions(
            load_config.roles,
            permission_registry,
            {owner: ["admin"] for owner in owners},
            [],
        ),
    ) == {"shared_view": {ALPHA: all_visuals[(ALPHA, "shared_view")]}}
