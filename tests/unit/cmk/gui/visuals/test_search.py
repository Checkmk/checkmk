#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.i18n import _l
from cmk.gui.pages import PageContext
from cmk.gui.permissions import (
    all_permissions,
    permission_registry,
)
from cmk.gui.search.matchers import match_item_generator_registry, MatchItemConfig
from cmk.gui.search.permissions import category_permissions_handler_registry
from cmk.gui.type_defs import Visual
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.visuals import BuiltinVisualsSearch, CustomVisualsSearch
from cmk.gui.visuals._search import (
    BuiltinVisualsMatchItemGenerator,
    BuiltinVisualsPermissionsHandler,
    CustomVisualsMatchItemGenerator,
    CustomVisualsPermissionsHandler,
)

OWNER = UserId("owner")


def _visual(owner: UserId, name: str, title: str, *, packaged: bool = False) -> Visual:
    return Visual(
        owner=owner,
        name=name,
        context={},
        single_infos=[],
        add_context_to_title=False,
        title=title,
        description="",
        topic="overview",
        sort_index=99,
        is_show_more=False,
        icon=None,
        hidden=False,
        hidebutton=False,
        public=True,
        packaged=packaged,
        link_from={},
        main_menu_search_terms=["term"],
    )


@pytest.fixture(name="search")
def fixture_search() -> BuiltinVisualsSearch:
    all_visuals = {
        (UserId.builtin(), "allhosts"): _visual(UserId.builtin(), "allhosts", "All hosts"),
        (OWNER, "my_view"): _visual(OWNER, "my_view", "My view"),
    }
    return BuiltinVisualsSearch(
        what="views",
        topic=_l("Built-in views"),
        load_all=lambda: all_visuals,
        url=lambda name: f"clone.py?name={name}",
    )


@pytest.mark.usefixtures("request_context")
def test_match_items_cover_builtin_visuals_only(
    search: BuiltinVisualsSearch, load_config: Config
) -> None:
    generator = BuiltinVisualsMatchItemGenerator(search)

    match_items = list(
        generator.generate_match_items(
            UserPermissions(
                load_config.roles,
                all_permissions(),
                {},
                [],
            ),
            MatchItemConfig.from_config(load_config),
        )
    )

    assert [(item.title, item.topic, item.url) for item in match_items] == [
        ("All hosts", "Built-in views", "clone.py?name=allhosts")
    ]
    assert list(match_items[0].match_texts) == ["all hosts", "allhosts", "term"]


@pytest.mark.parametrize("what", ["views", "dashboards"])
def test_permissions_checked_by_visual_search_exist(what: str) -> None:
    assert f"general.edit_{what}" in permission_registry
    assert f"general.edit_foreign_{what}" in permission_registry


@pytest.mark.usefixtures("with_admin_login")
def test_permitted_builtin_visual_is_visible(
    search: BuiltinVisualsSearch, load_config: Config, with_admin_login: UserId
) -> None:
    handler = BuiltinVisualsPermissionsHandler(
        search,
        UserPermissions(
            load_config.roles,
            all_permissions(),
            {with_admin_login: ["admin"]},
            [],
        ),
    )

    visibility_check = handler.get_visibility_check(search.category)

    assert handler.may_see_category(search.category)
    assert visibility_check("clone.py?name=allhosts")
    assert not visibility_check("clone.py?name=my_view")


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_registered_builtin_views_are_visible_to_admin(load_config: Config) -> None:
    ctx = PageContext(
        config=load_config,
        request=request,
        session=session,
        transactions=transactions,
        user_permissions=UserPermissions.from_config(load_config, all_permissions()),
    )
    handler = category_permissions_handler_registry["builtin_views"].build(ctx)

    match_items = list(
        match_item_generator_registry["builtin_views"].generate_match_items(
            UserPermissions.from_config(load_config, all_permissions()),
            MatchItemConfig.from_config(load_config),
        )
    )

    visibility_check = handler.get_visibility_check("builtin_views")
    assert handler.may_see_category("builtin_views")
    assert match_items
    assert all(visibility_check(item.url) for item in match_items)


def _custom_search(logged_in_user: UserId) -> CustomVisualsSearch:
    all_visuals = {
        (UserId.builtin(), "allhosts"): _visual(UserId.builtin(), "allhosts", "All hosts"),
        (UserId.builtin(), "shipped"): _visual(
            UserId.builtin(), "shipped", "Shipped", packaged=True
        ),
        (logged_in_user, "mine"): _visual(logged_in_user, "mine", "Mine"),
        (OWNER, "theirs"): _visual(OWNER, "theirs", "Theirs"),
    }
    return CustomVisualsSearch(
        what="views",
        topic=_l("Custom views"),
        load_all=lambda: all_visuals,
        url=lambda name, owner: f"edit.py?name={name}&owner={owner}",
    )


@pytest.mark.usefixtures("request_context")
def test_match_items_cover_custom_visuals_only(load_config: Config) -> None:
    generator = CustomVisualsMatchItemGenerator(_custom_search(UserId("me")))

    match_items = generator.generate_match_items(
        UserPermissions(
            load_config.roles,
            all_permissions(),
            {},
            [],
        ),
        MatchItemConfig.from_config(load_config),
    )

    assert sorted((item.title, item.topic, item.url) for item in match_items) == [
        ("Mine", "Custom views", "edit.py?name=mine&owner=me"),
        ("Theirs", "Custom views", "edit.py?name=theirs&owner=owner"),
    ]


def test_custom_visuals_are_reindexed_when_visuals_of_their_type_are_saved() -> None:
    generator = CustomVisualsMatchItemGenerator(_custom_search(UserId("me")))

    assert generator.is_affected_by_change("save-views")
    assert not generator.is_affected_by_change("save-dashboards")


def test_custom_visuals_are_reindexed_when_users_are_edited() -> None:
    generator = CustomVisualsMatchItemGenerator(_custom_search(UserId("me")))

    assert generator.is_affected_by_change("edit-users")


def test_user_sees_own_custom_visuals_only(with_user_login: UserId) -> None:
    handler = CustomVisualsPermissionsHandler(_custom_search(with_user_login))

    visibility_check = handler.get_visibility_check("custom_views")

    assert handler.may_see_category("custom_views")
    assert visibility_check(f"edit.py?name=mine&owner={with_user_login}")
    assert not visibility_check("edit.py?name=theirs&owner=owner")


def test_admin_sees_foreign_custom_visuals(with_admin_login: UserId) -> None:
    handler = CustomVisualsPermissionsHandler(_custom_search(with_admin_login))

    visibility_check = handler.get_visibility_check("custom_views")

    assert visibility_check(f"edit.py?name=mine&owner={with_admin_login}")
    assert visibility_check("edit.py?name=theirs&owner=owner")
