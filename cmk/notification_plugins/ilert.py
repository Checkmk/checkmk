#!/usr/bin/env python3
# iLert Checkmk Native Plug-in

# Copyright (c) 2013-2020, iLert GmbH
#       iLert <support@ilert.com>
# License: GNU Public License v2

from cmk.notification_plugins.utils import (
    get_password_from_env_or_context,
    JsonFieldMatcher,
    post_request,
    process_by_matchers,
    ResponseMatcher,
    StateInfo,
    StatusCodeMatcher,
    StatusCodeRange,
)

PLUGIN_VERSION = "1.0"

HEADERS = {
    "Content-type": "application/json",
    "Accept": "application/json",
    "Agent": "checkmk/extension/%s" % PLUGIN_VERSION,
}

RESULT_MATCHER: list[tuple[ResponseMatcher | StatusCodeRange, StateInfo]] = [
    ((200, 299), StateInfo(0, "json", "incidentKey")),
    ((300, 399), StateInfo(2, "str", "Error")),
    (
        StatusCodeMatcher(range=(400, 400)).and_(
            JsonFieldMatcher(field="code", value="NONE_OPEN_FOR_KEY")
        ),
        StateInfo(0, "str", "Event already closed in iLert"),
    ),
    ((400, 428), StateInfo(2, "str", "Event not accepted by iLert")),
    ((429, 429), StateInfo(1, "str", "Too many requests, will try again. Server response")),
    ((430, 499), StateInfo(2, "str", "Event not accepted by iLert")),
    ((500, 599), StateInfo(1, "str", "Server error")),
]


def _ilert_url() -> str:
    password = get_password_from_env_or_context(key="NOTIFY_PARAMETER_ILERT_API_KEY")
    return f"https://api.ilert.com/api/v1/events/checkmk-ext/{password}"


def main() -> int:
    return process_by_matchers(
        post_request(lambda context: {**context}, url=_ilert_url(), headers=HEADERS), RESULT_MATCHER
    )
