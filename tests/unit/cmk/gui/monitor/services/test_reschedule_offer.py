#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from cmk.gui.monitor.services._api._reschedule_offer import build_reschedule_offer
from cmk.gui.monitor.services._models import CheckType
from cmk.gui.openapi.framework.model import ApiOmitted

from .testlib import login_with, ServiceFactory

_RESCHEDULE_PERMISSION = "action.reschedule"


@pytest.fixture(name="may_reschedule")
def _may_reschedule() -> Iterator[None]:
    with login_with({_RESCHEDULE_PERMISSION: True}):
        yield


pytestmark = pytest.mark.usefixtures("request_context", "may_reschedule")


# The factory randomises every field, so each test pins the whole decision tree and varies the
# one thing it is about.
_ACTIVE_OWN_CHECK = {
    "check_type": CheckType.ACTIVE,
    "active_checks_enabled": True,
    "check_command": "check_tcp",
    "cached_at": None,
    "cache_interval": 0,
}


def test_active_service_reschedules_itself() -> None:
    offer = build_reschedule_offer(ServiceFactory.build(name="CPU load", **_ACTIVE_OWN_CHECK))

    assert offer is not None
    assert offer.target == "CPU load"
    assert offer.label == "Reschedule check"
    assert offer.icon_name == "reload"


def test_agent_based_service_reschedules_the_check_mk_service() -> None:
    offer = build_reschedule_offer(
        ServiceFactory.build(
            name="Check_MK Agent", **{**_ACTIVE_OWN_CHECK, "check_command": "check_mk-check_mk"}
        )
    )

    assert offer is not None
    assert offer.target == "Check_MK"
    assert offer.label == "Reschedule 'Check_MK' service"
    assert offer.icon_name == "reload-cmk"


def test_the_check_mk_service_itself_reschedules_itself() -> None:
    # Its check command is "check-mk", not "check_mk-", so the redirect does not apply to it.
    offer = build_reschedule_offer(
        ServiceFactory.build(name="Check_MK", **{**_ACTIVE_OWN_CHECK, "check_command": "check-mk"})
    )

    assert offer is not None
    assert offer.target == "Check_MK"
    assert offer.label == "Reschedule check"


def test_cached_service_is_blocked_and_says_how_old_the_cache_is() -> None:
    offer = build_reschedule_offer(
        ServiceFactory.build(
            name="CPU load",
            **{**_ACTIVE_OWN_CHECK, "cached_at": 1_752_405_510, "cache_interval": 300},
        )
    )

    assert offer is not None
    assert isinstance(offer.target, ApiOmitted)
    assert offer.icon_name == "cannot-reschedule"
    assert offer.tooltip.startswith(
        "This service is based on cached agent data and cannot be rescheduled."
    )
    assert "cache interval" in offer.tooltip


def test_passive_service_without_cache_is_blocked_for_being_passive() -> None:
    offer = build_reschedule_offer(
        ServiceFactory.build(
            name="A passive check",
            **{
                **_ACTIVE_OWN_CHECK,
                "check_type": CheckType.PASSIVE,
                "active_checks_enabled": False,
            },
        )
    )

    assert offer is not None
    assert isinstance(offer.target, ApiOmitted)
    assert offer.icon_name == "cannot-reschedule"
    assert offer.tooltip == "This service is checked passively and cannot be rescheduled."


_SHADOW_REFUSAL = "This service is monitored by a remote site and cannot be rescheduled here."


def test_shadow_service_is_blocked_for_being_remote() -> None:
    offer = build_reschedule_offer(
        ServiceFactory.build(
            name="CPU load", **{**_ACTIVE_OWN_CHECK, "check_type": CheckType.SHADOW}
        )
    )

    assert offer is not None
    assert isinstance(offer.target, ApiOmitted)
    assert offer.icon_name == "cannot-reschedule"
    assert offer.tooltip == _SHADOW_REFUSAL


def test_cached_shadow_service_is_blocked_for_being_remote() -> None:
    # Shadow wins over cached: this site cannot command a remote site's object either way, and
    # blaming the cache would send the user looking in the wrong place.
    offer = build_reschedule_offer(
        ServiceFactory.build(
            name="CPU load",
            **{
                **_ACTIVE_OWN_CHECK,
                "check_type": CheckType.SHADOW,
                "cached_at": 1_752_405_510,
            },
        )
    )

    assert offer is not None
    assert offer.tooltip == _SHADOW_REFUSAL


def test_user_without_the_permission_is_offered_nothing() -> None:
    with login_with({_RESCHEDULE_PERMISSION: False}):
        assert build_reschedule_offer(ServiceFactory.build(**_ACTIVE_OWN_CHECK)) is None
