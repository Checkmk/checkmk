# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC
from http import HTTPStatus

import pytest
import requests
import responses
from responses import matchers
from urllib3 import HTTPSConnectionPool
from urllib3.exceptions import ReadTimeoutError

from cmk.plugins.prism.special_agent.v4_client import PrismV4Client, PrismV4Error
from cmk.plugins.prism.special_agent.v4_rate_limits import endpoint_of, RateLimits

from .v4_testing import (
    BASE_URL,
    FakeClock,
    LIMIT_TOO_LARGE,
    LOGIN_REJECTED,
    page,
    page_matcher,
    PASSWORD,
    SERVER,
    USERNAME,
    v4_url,
    VM_NOT_FOUND,
    with_basic_auth,
    without_basic_auth,
)

VMS_PATH = "vmm/v4.0/ahv/config/vms"
CLUSTER_STATS_PATH = "clustermgmt/v4.0/stats/clusters/c1"
VM_STATS_PATH = "vmm/v4.0/ahv/stats/vms"
NOW = datetime(2026, 10, 21, 5, 32, tzinfo=UTC)
# Any cookie name works, the client sends back whatever Prism Central sets
SESSION_COOKIE = {"Set-Cookie": "SOME_SESSION=token; Path=/; Secure; HttpOnly"}
CERT_CHECKS = [
    pytest.param(True, id="certificate checked"),
    pytest.param("pc.cert.example.com", id="certificate name checked"),
]


def _vms(count: int) -> list[dict[str, str]]:
    return [{"extId": f"vm{i}"} for i in range(count)]


def _client(
    cert_check: bool | str = True,
    deadline: float | None = None,
    clock: FakeClock | None = None,
) -> PrismV4Client:
    clock = FakeClock() if clock is None else clock
    return PrismV4Client(
        BASE_URL,
        USERNAME,
        PASSWORD,
        cert_check,
        timeout=10,
        deadline=clock.now + 60 if deadline is None else deadline,
        now=lambda: NOW,
        rate_limits=RateLimits(clock=clock, sleep=clock.sleep),
        clock=clock,
    )


def test_requests_carry_the_cert_check_setting(api: responses.RequestsMock) -> None:
    api.get(
        v4_url(VMS_PATH),
        json={},
        match=[matchers.request_kwargs_matcher({"verify": False})],
    )

    assert _client(cert_check=False).get(VMS_PATH) == {}


def test_first_request_authenticates_with_the_password(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), json={}, match=[with_basic_auth()])

    assert _client().get(VMS_PATH) == {}


@pytest.mark.parametrize("cert_check", CERT_CHECKS)
def test_session_cookie_replaces_the_password(
    api: responses.RequestsMock, cert_check: bool | str
) -> None:
    api.get(v4_url(VMS_PATH), json={}, headers=SESSION_COOKIE, match=[with_basic_auth()])
    api.get(
        v4_url(VMS_PATH),
        json={"second": True},
        match=[without_basic_auth, matchers.header_matcher({"Cookie": "SOME_SESSION=token"})],
    )
    client = _client(cert_check)
    client.get(VMS_PATH)

    assert client.get(VMS_PATH) == {"second": True}


def test_rotated_session_cookie_is_followed(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), json={}, headers=SESSION_COOKIE, match=[with_basic_auth()])
    api.get(
        v4_url(VMS_PATH),
        json={},
        headers={"Set-Cookie": "SOME_SESSION=rotated; Path=/; Secure; HttpOnly"},
        match=[matchers.header_matcher({"Cookie": "SOME_SESSION=token"})],
    )
    api.get(
        v4_url(VMS_PATH),
        json={"third": True},
        match=[matchers.header_matcher({"Cookie": "SOME_SESSION=rotated"})],
    )
    client = _client()
    client.get(VMS_PATH)
    client.get(VMS_PATH)

    assert client.get(VMS_PATH) == {"third": True}


@pytest.mark.parametrize("cert_check", CERT_CHECKS)
def test_expired_session_cookie_is_renewed_with_the_password(
    api: responses.RequestsMock, cert_check: bool | str
) -> None:
    api.get(v4_url(VMS_PATH), json={}, headers=SESSION_COOKIE, match=[with_basic_auth()])
    api.get(v4_url(VMS_PATH), status=HTTPStatus.UNAUTHORIZED, match=[without_basic_auth])
    api.get(v4_url(VMS_PATH), json={"renewed": True}, match=[with_basic_auth()])
    client = _client(cert_check)
    client.get(VMS_PATH)

    assert client.get(VMS_PATH) == {"renewed": True}


@pytest.mark.parametrize(
    "status, body, message",
    [
        pytest.param(
            HTTPStatus.UNAUTHORIZED, LOGIN_REJECTED, "HTTP 401 invalid credentials", id="login"
        ),
        pytest.param(
            HTTPStatus.NOT_FOUND, VM_NOT_FOUND, "HTTP 404 Failed to perform", id="AppMessage"
        ),
        pytest.param(
            HTTPStatus.BAD_REQUEST,
            LIMIT_TOO_LARGE,
            r"HTTP 400 Numeric instance is greater than the required maximum",
            id="SchemaValidationError",
        ),
    ],
)
def test_error_message_of_prism_central_is_reported(
    api: responses.RequestsMock, status: HTTPStatus, body: dict[str, object], message: str
) -> None:
    api.get(v4_url(VMS_PATH), status=status, json=body)

    with pytest.raises(PrismV4Error, match=message):
        _client().get(VMS_PATH)


def test_error_response_with_success_status_raises(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), json=VM_NOT_FOUND)

    with pytest.raises(PrismV4Error, match="reports an error: Failed to perform"):
        _client().get(VMS_PATH)


def test_response_flagged_with_error_raises(api: responses.RequestsMock) -> None:
    api.get(
        v4_url(VMS_PATH),
        json={"data": [], "metadata": {"flags": [{"name": "hasError", "value": True}]}},
    )

    with pytest.raises(PrismV4Error, match="reports an error"):
        _client().get(VMS_PATH)


def test_read_timeout_while_reading_the_body_is_reported_as_timeout(
    api: responses.RequestsMock,
) -> None:
    api.get(
        v4_url(VMS_PATH),
        body=requests.exceptions.ConnectionError(
            ReadTimeoutError(HTTPSConnectionPool(SERVER), VMS_PATH, "Read timed out.")
        ),
    )

    with pytest.raises(PrismV4Error, match=f"^{VMS_PATH}: timed out$"):
        _client().get(VMS_PATH)


def test_connection_failure_is_reported_briefly(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), body=requests.exceptions.ConnectionError("Max retries exceeded"))

    with pytest.raises(PrismV4Error, match=f"^{VMS_PATH}: connection failed$"):
        _client().get(VMS_PATH)


def test_rate_limited_call_is_retried(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), status=HTTPStatus.TOO_MANY_REQUESTS)
    api.get(v4_url(VMS_PATH), json={"retried": True})

    assert _client().get(VMS_PATH) == {"retried": True}


def test_rate_limited_call_waits_for_retry_after(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), status=HTTPStatus.TOO_MANY_REQUESTS, headers={"Retry-After": "2"})
    api.get(v4_url(VMS_PATH), json={})
    clock = FakeClock()

    _client(clock=clock).get(VMS_PATH)

    assert clock.now == 102.0


def test_persistent_rate_limit_raises(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), status=HTTPStatus.TOO_MANY_REQUESTS)

    with pytest.raises(PrismV4Error, match=f"^{VMS_PATH}: HTTP 429 ") as error:
        _client().get(VMS_PATH)

    assert (error.value.status, len(api.calls)) == (HTTPStatus.TOO_MANY_REQUESTS, 4)


def test_rate_limited_call_without_time_to_retry_reports_the_refusal(
    api: responses.RequestsMock,
) -> None:
    api.get(v4_url(VMS_PATH), status=HTTPStatus.TOO_MANY_REQUESTS, headers={"Retry-After": "5"})
    clock = FakeClock()

    with pytest.raises(PrismV4Error, match=f"^{VMS_PATH}: HTTP 429 ") as error:
        _client(deadline=clock.now + 3, clock=clock).get(VMS_PATH)

    assert (error.value.status, len(api.calls), clock.now) == (
        HTTPStatus.TOO_MANY_REQUESTS,
        1,
        100.0,
    )


def test_rate_limit_that_outlasts_the_time_budget_fails_at_once(
    api: responses.RequestsMock,
) -> None:
    api.get(
        v4_url(VMS_PATH),
        json={},
        headers={
            "x-api-ratelimit-limit": "7",
            "x-api-ratelimit-remaining": "0",
            "x-api-ratelimit-refresh-period-seconds": "60",
        },
    )
    clock = FakeClock()
    client = _client(deadline=clock.now + 40, clock=clock)
    client.get(VMS_PATH)

    with pytest.raises(PrismV4Error, match="rate limit leaves no time"):
        client.get(VMS_PATH)

    assert (len(api.calls), clock.now) == (1, 100.0)


@pytest.mark.usefixtures("api")
def test_used_up_time_budget_raises_without_a_request() -> None:
    with pytest.raises(PrismV4Error, match="time budget"):
        _client(deadline=FakeClock().now - 1).get(VMS_PATH)


def test_list_all_follows_the_next_link(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), json=page(_vms(100), has_next=True), match=[page_matcher(0)])
    api.get(
        v4_url(VMS_PATH), json=page([{"extId": "last"}], has_next=False), match=[page_matcher(1)]
    )

    assert len(_client().list_all(VMS_PATH)) == 101


def test_list_all_stops_without_a_next_link(api: responses.RequestsMock) -> None:
    api.get(v4_url(VMS_PATH), json=page(_vms(100), has_next=False), match=[page_matcher(0)])

    assert len(_client().list_all(VMS_PATH)) == 100


def test_list_all_follows_a_short_page_with_a_next_link(api: responses.RequestsMock) -> None:
    api.get(
        v4_url(VMS_PATH), json=page([{"extId": "first"}], has_next=True), match=[page_matcher(0)]
    )
    api.get(
        v4_url(VMS_PATH), json=page([{"extId": "last"}], has_next=False), match=[page_matcher(1)]
    )

    assert _client().list_all(VMS_PATH) == [{"extId": "first"}, {"extId": "last"}]


def test_entity_stats_are_returned_raw_for_the_requested_window(
    api: responses.RequestsMock,
) -> None:
    series = {"hypervisorCpuUsagePpm": [{"timestamp": "2026-10-21T05:30:00Z", "value": 1}]}
    api.get(
        v4_url(CLUSTER_STATS_PATH),
        json={"data": series},
        match=[
            matchers.query_param_matcher(
                {
                    "$startTime": "2026-10-21T02:32:00Z",
                    "$endTime": "2026-10-21T05:32:00Z",
                    "$samplingInterval": "3600",
                    "$statType": "AVG",
                    "$select": "hypervisorCpuUsagePpm",
                }
            )
        ],
    )

    stats = _client().entity_stats(
        CLUSTER_STATS_PATH,
        window=timedelta(hours=3),
        sampling_interval=timedelta(hours=1),
        stat_type="AVG",
        select=["hypervisorCpuUsagePpm"],
    )

    assert stats == series


def test_vm_stats_always_select_the_sample_timestamp(api: responses.RequestsMock) -> None:
    api.get(
        v4_url(VM_STATS_PATH),
        json=page([{"extId": "vm1", "stats": []}], has_next=False),
        match=[
            matchers.query_param_matcher(
                {"$select": "extId,stats/hypervisorCpuUsagePpm,stats/timestamp"},
                strict_match=False,
            )
        ],
    )

    stats = _client().list_stats(
        VM_STATS_PATH,
        window=timedelta(minutes=5),
        sampling_interval=timedelta(minutes=5),
        select=["extId", "stats/hypervisorCpuUsagePpm"],
    )

    assert stats == [{"extId": "vm1", "stats": []}]


def test_client_keeps_to_the_rate_limit_a_response_reports(api: responses.RequestsMock) -> None:
    api.get(
        v4_url(VMS_PATH),
        json={},
        headers={
            "x-api-ratelimit-limit": "7",
            "x-api-ratelimit-remaining": "6",
            "x-api-ratelimit-refresh-period-seconds": "1",
        },
    )
    clock = FakeClock()
    limits = RateLimits(clock=clock, sleep=clock.sleep)
    client = PrismV4Client(
        BASE_URL,
        USERNAME,
        PASSWORD,
        True,
        timeout=10,
        deadline=clock.now + 60,
        rate_limits=limits,
        clock=clock,
    )

    client.get(VMS_PATH)

    # The call above was the first of 7 in the window, the 8th has to wait
    assert [limits.reserve(endpoint_of(v4_url(VMS_PATH))) for _ in range(7)] == [
        *[0.0] * 6,
        1.0,
    ]


def test_call_that_fails_unexpectedly_does_not_hold_up_the_next(
    api: responses.RequestsMock,
) -> None:
    api.get(v4_url(VMS_PATH), body=ValueError("unexpected"))
    clock = FakeClock()
    limits = RateLimits(clock=clock, sleep=clock.sleep)
    client = PrismV4Client(
        BASE_URL,
        USERNAME,
        PASSWORD,
        True,
        timeout=10,
        deadline=clock.now + 60,
        rate_limits=limits,
        clock=clock,
    )
    with pytest.raises(ValueError):
        client.get(VMS_PATH)

    assert limits.reserve(endpoint_of(v4_url(VMS_PATH))) == 0.0
