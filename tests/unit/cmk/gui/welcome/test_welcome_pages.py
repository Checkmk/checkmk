#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

import json
from collections.abc import Iterator
from dataclasses import replace

import pytest

import cmk.utils.paths
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.htmllib.html import _load_vue_manifest
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import Page, PageContext, PageHandler, PageRegistry
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.welcome.pages import get_welcome_data, register
from cmk.gui.welcome.registry import welcome_card_registry, WelcomeCardCallback, WelcomeCardUrl
from cmk.shared_typing.welcome import FinishedEnum, WelcomeCards


@pytest.fixture(name="page_context")
def fixture_page_context() -> PageContext:
    return PageContext(config=Config(), request=request)


@pytest.fixture(name="installed_themes")
def fixture_installed_themes() -> None:
    """The main navigation of a full page offers the themes found on disk."""
    theme_base = cmk.utils.paths.web_dir / "htdocs/themes"
    for theme_id, title in (("facelift", "Light"), ("modern-dark", "Dark")):
        (theme_base / theme_id).mkdir(parents=True, exist_ok=True)
        (theme_base / theme_id / "theme.json").write_text(json.dumps({"title": title}))


@pytest.fixture(name="frontend_vue_manifest")
def fixture_frontend_vue_manifest() -> Iterator[None]:
    """Rendering a full page injects the frontend bundle from the manifest."""
    base = cmk.utils.paths.web_dir / "htdocs/cmk-frontend-vue"
    base.mkdir(parents=True, exist_ok=True)
    (base / ".manifest.json").write_text(
        json.dumps(
            {
                "src/main.ts": {"file": "main.js"},
                "src/nav_sidebar.ts": {"file": "nav_sidebar.js"},
                "src/stage1.ts": {"file": "stage1.js"},
            }
        )
    )
    _load_vue_manifest.cache_clear()
    yield
    _load_vue_manifest.cache_clear()


@pytest.fixture(name="pages")
def fixture_pages() -> PageRegistry:
    page_registry = PageRegistry()
    register(page_registry)
    return page_registry


@pytest.fixture(name="without_edition_cards")
def fixture_without_edition_cards() -> Iterator[None]:
    registered = list(welcome_card_registry.values())
    welcome_card_registry.clear()
    try:
        yield
    finally:
        welcome_card_registry.clear()
        for card in registered:
            welcome_card_registry.register(card)


def _cards() -> WelcomeCards:
    cards = get_welcome_data().cards
    assert cards is not None
    return cards


def _handler(page_registry: PageRegistry, ident: str) -> PageHandler:
    handler = page_registry[ident].handler
    return handler.handle_page if isinstance(handler, Page) else handler


def test_add_host_card_defaults_to_the_new_host_page(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    add_host = _cards().add_host

    assert "wato.py" in add_host
    assert "mode=newhost" in add_host


def test_add_host_card_prefers_the_registered_card(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    welcome_card_registry.register(
        WelcomeCardUrl(id="add_host", vars=[("mode", "quick_setup")], filename="wato.py")
    )

    assert "mode=quick_setup" in _cards().add_host


def test_card_registered_with_a_callback_yields_its_callback_id(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    welcome_card_registry.register(
        WelcomeCardCallback(id="relays", callback_id="open_relay_dialog")
    )

    assert _cards().relays == "open_relay_dialog"


def test_card_without_a_registered_entry_has_no_link(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    assert _cards().license_site is None


def test_completed_steps_are_reported_in_stage_order(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    user.welcome_completed_steps = {step.value for step in FinishedEnum}

    finished = get_welcome_data().stage_information.finished

    assert finished == [
        FinishedEnum.add_host,
        FinishedEnum.activate_changes,
        FinishedEnum.adjust_services,
        FinishedEnum.assign_responsibilities,
        FinishedEnum.enable_notifications,
        FinishedEnum.create_dashboard,
    ]


def test_only_the_completed_steps_are_reported_as_finished(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    user.welcome_completed_steps = {"add_host", "create_dashboard"}

    finished = get_welcome_data().stage_information.finished

    assert finished == [FinishedEnum.add_host, FinishedEnum.create_dashboard]


def test_no_step_is_finished_for_a_fresh_user(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    assert get_welcome_data().stage_information.finished == []


def test_welcome_is_flagged_as_start_page_when_the_user_chose_it(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    user.save_file("start_url", "welcome.py")

    assert get_welcome_data().is_start_url is True


def test_welcome_is_not_flagged_as_start_page_by_default(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    assert get_welcome_data().is_start_url is False


def test_marking_a_step_complete_stores_it(
    with_admin_login: UserId,
    without_edition_cards: None,
    pages: PageRegistry,
    page_context: PageContext,
) -> None:
    request.set_var("_completed_step", "add_host")

    _handler(pages, "ajax_mark_step_as_complete")(page_context)

    assert user.welcome_completed_steps == {"add_host"}


def test_marking_an_unknown_step_complete_is_ignored(
    with_admin_login: UserId,
    without_edition_cards: None,
    pages: PageRegistry,
    page_context: PageContext,
) -> None:
    request.set_var("_completed_step", "conquer_the_world")

    _handler(pages, "ajax_mark_step_as_complete")(page_context)

    assert user.welcome_completed_steps == set()


def test_stage_information_page_reports_the_finished_steps(
    with_admin_login: UserId,
    without_edition_cards: None,
    pages: PageRegistry,
    page_context: PageContext,
) -> None:
    user.welcome_completed_steps = {"activate_changes"}
    stage_information = pages["ajax_get_welcome_page_stage_information"].handler
    assert isinstance(stage_information, Page)

    assert stage_information.page(page_context) == {"finished": [FinishedEnum.activate_changes]}


def test_welcome_page_renders_the_welcome_component(
    installed_themes: None,
    with_admin_login: UserId,
    without_edition_cards: None,
    frontend_vue_manifest: None,
    patch_theme: None,
    pages: PageRegistry,
    page_context: PageContext,
) -> None:
    with output_funnel.plugged():
        _handler(pages, "welcome")(page_context)
        rendered = output_funnel.drain()

    assert "cmk-welcome" in rendered


def test_welcome_page_sends_users_without_setup_permissions_to_the_start_page(
    installed_themes: None,
    with_user_login: UserId,
    without_edition_cards: None,
    frontend_vue_manifest: None,
    patch_theme: None,
    pages: PageRegistry,
) -> None:
    ctx = PageContext(config=replace(Config(), start_url="index.py"), request=request)

    with output_funnel.plugged():
        _handler(pages, "welcome")(ctx)
        rendered = output_funnel.drain()

    assert "index.py" in rendered
    assert "cmk-welcome" not in rendered


def test_welcome_page_falls_back_to_the_dashboard_for_a_rejected_start_page(
    installed_themes: None,
    with_user_login: UserId,
    without_edition_cards: None,
    frontend_vue_manifest: None,
    patch_theme: None,
    pages: PageRegistry,
) -> None:
    ctx = PageContext(
        config=replace(Config(), start_url="http://phishing.example.com"), request=request
    )

    with output_funnel.plugged():
        _handler(pages, "welcome")(ctx)
        rendered = output_funnel.drain()

    assert "dashboard.py" in rendered
    assert "phishing.example.com" not in rendered
