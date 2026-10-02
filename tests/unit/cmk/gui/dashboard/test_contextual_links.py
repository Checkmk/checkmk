#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.dashboard.api import (
    EffectiveLink,
    ExplicitWidgetContent,
    resolve_widget,
    SavedWidgetContent,
)
from cmk.gui.dashboard.api.model.contextual_link import (
    ContextualLinkDefault,
    ContextualLinkInherited,
    ContextualLinkNone,
    ContextualLinkSpec,
    VisualLocation,
)
from cmk.gui.dashboard.api.model.widget_content._base import BaseWidgetContent
from cmk.gui.dashboard.api.model.widget_content.stats import EventStatsContent, HostStatsContent
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from tests.unit.cmk.gui.helpers.dashboard_widget_resolution_test_helper import (
    api_context,
    dashboard_token,
    dashboard_widget,
    impersonating,
    WIDGET_ID,
)

_BUILT_IN = EffectiveLink(
    title="All hosts",
    location=VisualLocation(type="views", name="searchhost"),
    include_context=True,
    include_time_range=False,
    show_filter_form=True,
)
_TYPES = frozenset({"hoststats", "eventstats"})

_SEARCHHOST = VisualLocation(type="views", name="searchhost")
_INHERITED = ContextualLinkInherited(
    type="inherited",
    location=_SEARCHHOST,
    include_context=False,
    include_time_range=True,
    show_filter_form=False,
)


def _linked(contextual_link: ContextualLinkSpec) -> HostStatsContent:
    return HostStatsContent(type="host_stats", contextual_link=contextual_link)


def _links(
    content: BaseWidgetContent, user_permissions: UserPermissions | None = None
) -> Sequence[EffectiveLink]:
    source = ExplicitWidgetContent(type="explicit", content=content, context={})
    with resolve_widget(
        api_context(None, user_permissions), source, _TYPES, lambda _content: _BUILT_IN
    ) as widget:
        return widget.links


@pytest.mark.usefixtures("load_config", "request_context")
def test_a_content_without_a_link_field_resolves_the_built_in_link() -> None:
    assert _links(EventStatsContent(type="event_stats")) == [_BUILT_IN]


@pytest.mark.usefixtures("load_config", "request_context")
def test_default_resolves_the_built_in_link() -> None:
    assert _links(_linked(ContextualLinkDefault(type="default"))) == [_BUILT_IN]


@pytest.mark.usefixtures("load_config", "request_context")
def test_none_resolves_no_link() -> None:
    assert _links(_linked(ContextualLinkNone(type="none"))) == []


@pytest.mark.usefixtures("load_config", "request_context")
def test_inherited_resolves_one_link_with_its_flags() -> None:
    [link] = _links(_linked(_INHERITED))

    assert link.location == _SEARCHHOST
    assert (link.include_context, link.include_time_range, link.show_filter_form) == (
        False,
        True,
        False,
    )


@pytest.mark.usefixtures("load_config", "request_context")
def test_the_saved_arm_resolves_no_link(monkeypatch: pytest.MonkeyPatch) -> None:
    impersonating(monkeypatch, {WIDGET_ID: dashboard_widget()})
    source = SavedWidgetContent(type="saved", widget_id=WIDGET_ID)

    with resolve_widget(
        api_context(dashboard_token()), source, _TYPES, lambda _content: _BUILT_IN
    ) as widget:
        assert widget.links == []


@pytest.mark.usefixtures("load_config", "request_context")
def test_an_inherited_link_to_a_forbidden_target_resolves_with_the_stored_name() -> None:
    [link] = _links(_linked(_INHERITED), UserPermissions({}, {}, {}, []))

    assert link.title == "searchhost"


def test_an_inherited_link_takes_the_title_of_a_readable_target(
    load_config: Config, with_admin_login: UserId
) -> None:
    admin_permissions = UserPermissions(
        load_config.roles, permission_registry, {with_admin_login: ["admin"]}, []
    )

    [link] = _links(_linked(_INHERITED), admin_permissions)

    assert link.title == "Host search"
