# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.prism.special_agent.v4_rate_limits import endpoint_of, PROBE_POLL, RateLimits

from .v4_testing import FakeClock

STATS = "clustermgmt/v4.0/stats/storage-containers/{extId}"
VMS = "vmm/v4.0/ahv/config/vms"

# What Prism Central 7.5 answered for the container stats
LIMITED = {
    "x-api-ratelimit-limit": "10",
    "x-api-ratelimit-remaining": "9",
    "x-api-ratelimit-refresh-period-seconds": "1",
    "x-ratelimit-limit": "80",
    "x-ratelimit-remaining": "79",
}


def _limits(clock: FakeClock) -> RateLimits:
    return RateLimits(clock=clock, sleep=clock.sleep)


def test_calls_for_different_entities_count_against_one_endpoint() -> None:
    assert (
        endpoint_of(
            "https://pc:9440/api/clustermgmt/v4.0/stats/storage-containers/"
            "58973d0f-3460-49fa-9c29-e94958c51fa8?$statType=LAST"
        )
        == "https://pc:9440/api/" + STATS
    )


def test_first_call_to_an_endpoint_goes_alone() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)

    assert limits.reserve(STATS) == PROBE_POLL


def test_calls_follow_once_the_first_response_reported_the_limit() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, LIMITED)

    assert [limits.reserve(STATS) for _ in range(9)] == [0.0] * 9


def test_call_beyond_the_limit_waits_for_the_window_to_pass() -> None:
    clock = FakeClock()
    limits = _limits(clock)
    limits.reserve(STATS)
    limits.update(STATS, LIMITED)
    for _ in range(9):
        limits.reserve(STATS)
    clock.now += 0.25

    assert limits.reserve(STATS) == 0.75


def test_waiting_call_goes_once_the_window_has_passed() -> None:
    clock = FakeClock()
    limits = _limits(clock)
    limits.reserve(STATS)
    limits.update(STATS, LIMITED)
    for _ in range(9):
        limits.reserve(STATS)

    acquired = limits.acquire(STATS, deadline=140.0)

    assert (acquired, clock.now) == (True, 101.0)


def test_endpoints_do_not_wait_for_each_other() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, LIMITED)
    for _ in range(9):
        limits.reserve(STATS)

    assert limits.reserve(VMS) == 0.0


def test_all_endpoints_together_stay_within_the_overall_limit() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, {**LIMITED, "x-ratelimit-limit": "3"})
    limits.reserve(VMS)
    limits.update(VMS, {**LIMITED, "x-ratelimit-limit": "3"})
    limits.reserve(STATS)

    assert limits.reserve(VMS) > 0


def test_no_calls_left_on_prism_central_blocks_until_the_window_passes() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, {**LIMITED, "x-api-ratelimit-remaining": "0"})

    assert limits.reserve(STATS) == 1.0


def test_endpoint_without_reported_limits_is_not_throttled() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, {})

    assert [limits.reserve(STATS) for _ in range(100)] == [0.0] * 100


def test_call_without_response_lets_the_next_one_find_out_the_limits() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.release(STATS)

    assert limits.reserve(STATS) == 0.0


def test_response_without_limits_keeps_the_limits_learned_before() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, LIMITED)
    limits.update(STATS, {})
    for _ in range(9):
        limits.reserve(STATS)

    assert limits.reserve(STATS) > 0


def test_failed_first_call_without_limits_lets_the_next_call_find_out() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, {}, succeeded=False)

    assert [limits.reserve(STATS), limits.reserve(STATS)] == [0.0, PROBE_POLL]


def test_fractional_refresh_period_sets_the_window() -> None:
    clock = FakeClock()
    limits = _limits(clock)
    limits.reserve(STATS)
    limits.update(STATS, {**LIMITED, "x-api-ratelimit-refresh-period-seconds": "0.5"})
    for _ in range(9):
        limits.reserve(STATS)

    assert limits.reserve(STATS) == 0.5


def test_limit_of_zero_waits_a_window_then_lets_one_call_find_out_the_limit() -> None:
    clock = FakeClock()
    limits = _limits(clock)
    limits.reserve(STATS)
    limits.update(STATS, {**LIMITED, "x-api-ratelimit-limit": "0"})
    during_window = limits.reserve(STATS)
    clock.now += 1

    assert (during_window, limits.reserve(STATS), limits.reserve(STATS)) == (
        1.0,
        0.0,
        PROBE_POLL,
    )


def test_refused_call_holds_back_the_endpoint_until_it_may_be_retried() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, LIMITED)

    limits.back_off(STATS, 2.0)

    assert (limits.reserve(STATS), limits.reserve(VMS)) == (2.0, 0.0)


def test_refused_call_without_retry_after_holds_back_the_endpoint_for_a_window() -> None:
    limits = _limits(FakeClock())
    limits.reserve(STATS)
    limits.update(STATS, LIMITED)

    limits.back_off(STATS, None)

    assert limits.reserve(STATS) == 1.0


def test_wait_past_the_deadline_gives_up_at_once() -> None:
    clock = FakeClock()
    limits = _limits(clock)
    limits.reserve(STATS)
    limits.update(
        STATS,
        {
            **LIMITED,
            "x-api-ratelimit-remaining": "0",
            "x-api-ratelimit-refresh-period-seconds": "60",
        },
    )

    acquired = limits.acquire(STATS, deadline=140.0)

    assert (acquired, clock.now) == (False, 100.0)
