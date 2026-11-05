#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

import pytest

from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.sidebar.main_menu import PageAjaxSidebarChangesMenu, PageAjaxSitesAndChanges


def _page_context(config: Config) -> PageContext:
    return PageContext(config=config, request=request)


@dataclasses.dataclass
class _EmptyPopout:
    """Stands in for the activation popout payload, which is only asdict()-ed here."""


class _PopoutRecorder:
    """Records which activation id reached the activation layer."""

    def __init__(self) -> None:
        self.activation_ids: list[str | None] = []

    def __call__(self, _sites: object, activation_id: str | None) -> _EmptyPopout:
        self.activation_ids.append(activation_id)
        return _EmptyPopout()


@pytest.mark.parametrize(
    "granted",
    [
        pytest.param("wato.activate", id="activate"),
        pytest.param("wato.see_pending_changes", id="see_pending_changes"),
    ],
)
def test_sites_and_changes_are_served_with_either_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config, granted: str
) -> None:
    recorder = _PopoutRecorder()
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda permission: permission == granted)
        m.setattr(
            "cmk.gui.watolib.activate_changes.ActivateChanges."
            "get_all_data_required_for_activation_popout",
            recorder,
        )
        PageAjaxSitesAndChanges().page(_page_context(load_config))

    assert recorder.activation_ids == [None]


def test_sites_and_changes_need_a_permission_to_see_them(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda permission: False)
        with pytest.raises(MKAuthException):
            PageAjaxSitesAndChanges().page(_page_context(load_config))


def test_pending_changes_count_is_zero_for_a_user_who_may_not_see_them(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda permission: False)
        result = PageAjaxSidebarChangesMenu().page(_page_context(load_config))

    assert result == {"number_of_pending_changes": 0}
