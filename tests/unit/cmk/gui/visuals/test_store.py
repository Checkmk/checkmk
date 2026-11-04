#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc.store import save_object_to_file
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.permissions import all_permissions
from cmk.gui.type_defs import Visual
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.visuals import available_by_owner, load, visual_permissions

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
            all_permissions(),
            {owner: ["admin"] for owner in owners},
            [],
        ),
    ) == {"shared_view": {ALPHA: all_visuals[(ALPHA, "shared_view")]}}


def _visual_from_raw(raw: dict[str, object]) -> Visual:
    visual = _published_visual(UserId.builtin(), "")
    visual["title"] = str(raw["title"])
    return visual


@pytest.fixture(name="packaged_view_path")
def fixture_packaged_view_path() -> Iterator[Path]:
    cmk.utils.paths.profile_dir.mkdir(parents=True, exist_ok=True)
    path = cmk.utils.paths.local_views_dir / "packaged_view"
    yield path
    path.unlink(missing_ok=True)


def test_load_returns_packaged_visual_added_after_previous_load(packaged_view_path: Path) -> None:
    load("views", {}, _visual_from_raw)
    save_object_to_file(
        packaged_view_path,
        {"packaged_view": {"title": "Packaged view", "public": True}},
    )

    visuals = load("views", {}, _visual_from_raw)

    assert visuals[(UserId.builtin(), "packaged_view")]["title"] == "Packaged view"


@pytest.mark.usefixtures("request_context")
def test_visual_permissions_contain_permission_of_packaged_visual(
    packaged_view_path: Path,
) -> None:
    save_object_to_file(
        packaged_view_path,
        {"packaged_view": {"title": "Packaged view", "public": True}},
    )

    permissions = visual_permissions("views", _visual_from_raw)

    assert "view.packaged_view_packaged" in {p.name for p in permissions}
