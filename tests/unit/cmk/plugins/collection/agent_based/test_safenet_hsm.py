# .1.3.6.1.4.1.12383.3.1.1.1.0 7645301
# .1.3.6.1.4.1.12383.3.1.1.2.0 134
# .1.3.6.1.4.1.12383.3.1.1.3.0 0
# .1.3.6.1.4.1.12383.3.1.1.4.0 3

import pytest

from cmk.agent_based.v1 import IgnoreResultsError
from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.safenet.agent_based.safenet_hsm import (
    check_safenet_hsm,
    check_safenet_hsm_events,
    EventStatCheckParamT,
    OperationStatCheckParamT,
    parse_safenet_hsm,
    Section,
)

STRING_TABLE = [
    ["7645301", "134", "0", "3"],
]

DEFAULT_EVENT_PARAMS: EventStatCheckParamT = {
    "critical_events": ("no_levels", None),
    "noncritical_events": ("no_levels", None),
    "critical_event_rate": ("no_levels", None),
    "noncritical_event_rate": ("no_levels", None),
}

DEFAULT_OPS_PARAMS: OperationStatCheckParamT = {
    "error_rate": ("no_levels", None),
    "request_rate": ("no_levels", None),
    "operation_errors": ("no_levels", None),
}


def test_parse_safenet_hsm() -> None:
    assert parse_safenet_hsm(STRING_TABLE) == {
        "operation_requests": 7645301,
        "operation_errors": 134,
        "critical_events": 0,
        "noncritical_events": 3,
    }


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section | None:
    return parse_safenet_hsm(STRING_TABLE)


@pytest.mark.usefixtures("initialised_item_state")
def test_check_safenet_hsm_events(section: Section) -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_safenet_hsm_events(DEFAULT_EVENT_PARAMS, section))

    assert list(check_safenet_hsm_events(DEFAULT_EVENT_PARAMS, section)) == [
        Result(state=State.OK, summary="Critical Events: 0 Critical Events since last reset"),
        Metric("critical_events", 0.0),
        Result(state=State.OK, summary="Critical Events: 0.00 Critical Events/s"),
        Metric("critical_events", 0.0),
        Result(state=State.OK, summary="Noncritical Events: 3 Noncritical Events since last reset"),
        Metric("noncritical_events", 3.0),
        Result(state=State.OK, summary="Noncritical Events: 0.00 Noncritical Events/s"),
        Metric("noncritical_events", 0.0),
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_safenet_hsm_op_stats(section: Section) -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_safenet_hsm(DEFAULT_OPS_PARAMS, section))

    assert list(check_safenet_hsm(DEFAULT_OPS_PARAMS, section)) == [
        Result(state=State.OK, summary="Errors: 134 Errors since last reset"),
        Metric("operation_errors", 134.0),
        Result(state=State.OK, summary="Errors: 0.00 Errors/s"),
        Metric("operation_errors", 0.0),
        Result(state=State.OK, summary="Requests: 0.00 Requests/s"),
        Metric("operation_requests", 0.0),
    ]
