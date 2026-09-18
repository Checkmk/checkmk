#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.welcome.registry import WelcomeCardCallback, WelcomeCardRegistry, WelcomeCardUrl


def test_url_card_is_looked_up_by_its_id() -> None:
    registry = WelcomeCardRegistry()
    card = WelcomeCardUrl(id="add_host", vars=[("mode", "newhost")], filename="wato.py")

    registry.register(card)

    assert registry["add_host"] is card


def test_callback_card_is_looked_up_by_its_id() -> None:
    registry = WelcomeCardRegistry()
    card = WelcomeCardCallback(id="relays", callback_id="open_relay_dialog")

    registry.register(card)

    assert registry["relays"] is card
