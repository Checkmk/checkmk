#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import pytest

from cmk.gui.utils.security_log_events import (
    AuthenticationFailureEvent,
    AuthenticationInitiatedEvent,
    AuthenticationSuccessEvent,
)

type _AnyAuthEvent = (
    AuthenticationFailureEvent | AuthenticationInitiatedEvent | AuthenticationSuccessEvent
)


def _failure(extra_details: dict[str, str] | None) -> AuthenticationFailureEvent:
    return AuthenticationFailureEvent(
        user_error="err",
        auth_method="cognito",
        username=None,
        remote_ip=None,
        extra_details=extra_details,
    )


def _initiated(extra_details: dict[str, str] | None) -> AuthenticationInitiatedEvent:
    return AuthenticationInitiatedEvent(
        auth_method="cognito", remote_ip=None, extra_details=extra_details
    )


def _success(extra_details: dict[str, str] | None) -> AuthenticationSuccessEvent:
    return AuthenticationSuccessEvent(
        auth_method="cognito", username=None, remote_ip=None, extra_details=extra_details
    )


@pytest.mark.parametrize("make_event", [_failure, _initiated, _success])
def test_extra_details_merged_into_event_details(
    make_event: Callable[[dict[str, str] | None], _AnyAuthEvent],
) -> None:
    assert make_event({"state": "abc12345"}).details["state"] == "abc12345"


@pytest.mark.parametrize("make_event", [_failure, _initiated, _success])
def test_extra_details_cannot_overwrite_baseline_fields(
    make_event: Callable[[dict[str, str] | None], _AnyAuthEvent],
) -> None:
    event = make_event({"user": "extra_user", "method": "extra_method", "remote_ip": "extra_ip"})
    assert event.details["user"] != "extra_user"
    assert event.details["method"] != "extra_method"
    assert event.details["remote_ip"] != "extra_ip"
