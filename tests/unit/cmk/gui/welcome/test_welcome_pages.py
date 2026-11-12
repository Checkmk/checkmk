#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.welcome.pages import get_welcome_data
from cmk.gui.welcome.registry import (
    welcome_card_registry,
    welcome_flag_registry,
    WelcomeCardDynamicUrl,
    WelcomeFlag,
)
from cmk.shared_typing.welcome import FinishedEnum, WelcomeCards


@pytest.fixture(name="without_edition_cards")
def fixture_without_edition_cards() -> Iterator[None]:
    cards, flags = list(welcome_card_registry.values()), list(welcome_flag_registry.values())
    welcome_card_registry.clear()
    welcome_flag_registry.clear()
    try:
        yield
    finally:
        welcome_card_registry.clear()
        welcome_flag_registry.clear()
        for card in cards:
            welcome_card_registry.register(card)
        for flag in flags:
            welcome_flag_registry.register(flag)


def _cards() -> WelcomeCards:
    cards = get_welcome_data(is_snapin=False).cards
    assert cards is not None
    return cards


def test_dynamic_card_links_to_the_vars_it_computes(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    welcome_card_registry.register(
        WelcomeCardDynamicUrl(
            id="network_devices",
            make_vars=lambda: [("mode", "newhost"), ("relayid", "relay1")],
            filename="wato.py",
        )
    )

    url = _cards().network_devices

    assert url is not None
    assert "mode=newhost" in url
    assert "relayid=relay1" in url


def test_dynamic_card_without_vars_has_no_link(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    welcome_card_registry.register(
        WelcomeCardDynamicUrl(
            id="network_devices",
            make_vars=lambda: None,
            filename="wato.py",
        )
    )

    assert _cards().network_devices is None


@pytest.mark.parametrize("configured", [True, False])
def test_relay_flag_says_what_the_registered_flag_says(
    with_admin_login: UserId,
    without_edition_cards: None,
    configured: bool,
) -> None:
    welcome_flag_registry.register(WelcomeFlag(id="relay_configured", value=lambda: configured))

    assert _cards().relay_configured is configured


def test_relay_flag_is_not_sent_without_the_relay_feature(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    assert _cards().relay_configured is None


def test_completed_steps_are_reported_in_stage_order(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    user.welcome_completed_steps = {step.value for step in FinishedEnum}

    assert get_welcome_data(is_snapin=False).stage_information.finished == [
        FinishedEnum.add_host,
        FinishedEnum.adjust_services,
        FinishedEnum.assign_responsibilities,
        FinishedEnum.enable_notifications,
        FinishedEnum.create_dashboard,
    ]


def test_retired_steps_are_not_reported_as_finished(
    with_admin_login: UserId,
    without_edition_cards: None,
) -> None:
    user.welcome_completed_steps = {"activate_changes"}

    assert get_welcome_data(is_snapin=False).stage_information.finished == []
