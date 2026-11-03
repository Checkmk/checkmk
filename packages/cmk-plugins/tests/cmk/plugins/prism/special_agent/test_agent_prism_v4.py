# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import json
import time
from collections.abc import Callable, Sequence
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

import pytest
import responses

from cmk.plugins.prism.special_agent.agent_prism import agent_prism_main, parse_arguments
from cmk.plugins.prism.special_agent.agent_prism_v4 import (
    ClusterRouting,
    CLUSTERS_PATH,
    FetchContext,
    Fetcher,
    FetchSchedule,
    run_fetchers,
    Section,
    Unroutable,
    write_sections,
)
from cmk.plugins.prism.special_agent.v4_client import PrismV4Client, PrismV4Error
from cmk.server_side_programs.v1 import AgentMessages

from .v4_testing import (
    BASE_URL,
    FakeStorage,
    LOGIN_REJECTED,
    page_matcher,
    PASSWORD,
    SERVER,
    USERNAME,
    v4_url,
)


def recorded_clusters() -> dict[str, object]:
    """The cluster list of a Prism Central 7.5 lab (anonymised): one cluster and PC itself"""
    loaded: dict[str, object] = json.loads(
        (Path(__file__).parent / "v4_fixtures" / "clustermgmt_config_clusters.json").read_text()
    )
    return loaded


CLUSTER_ID = "000645cc-2b3a-3b1c-06a8-7cc255ec3615"
PRISM_CENTRAL_ID = "0806a141-8916-471b-99fd-b5119ff280ef"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _routing() -> ClusterRouting:
    clusters = recorded_clusters()["data"]
    assert isinstance(clusters, list)
    return ClusterRouting.from_clusters(clusters, AgentMessages())


def _context() -> FetchContext:
    client = PrismV4Client(
        BASE_URL,
        USERNAME,
        PASSWORD,
        True,
        timeout=10,
        deadline=time.monotonic() + 60,
    )
    return FetchContext(client, [], _routing())


def _sections_of(*sections: Section) -> Fetcher:
    return Fetcher("sections", lambda _context: sections)


def _denied(_context: FetchContext) -> Sequence[Section]:
    raise PrismV4Error("vmm/v4.0/ahv/config/vms: HTTP 403 Permission denied")


def _buggy(_context: FetchContext) -> Sequence[Section]:
    raise KeyError("extId")


def _slow_data() -> Fetcher:
    return Fetcher("disks", lambda _context: [Section("prism_disks_v2", {})], timedelta(minutes=10))


def _v4_args() -> list[str]:
    return [
        "--server",
        SERVER,
        "--username",
        USERNAME,
        "--password",
        PASSWORD,
        "--api-version",
        "v4",
    ]


def test_cluster_data_goes_to_host_named_after_cluster() -> None:
    assert _routing().host_for(CLUSTER_ID) == "cluster-a"


def test_prism_central_data_stays_on_prism_central_host() -> None:
    assert _routing().host_for(PRISM_CENTRAL_ID) is None


def test_unknown_cluster_is_not_routed() -> None:
    assert _routing().host_for("c-unknown") == Unroutable("unknown cluster c-unknown")


# Real extIds start with the creation time, so clusters created together share a long prefix.
# The newer one sorts first here, so only incarnationId can tell their age.
OLDER_TWIN = "000645cc-2b3a-3b1c-06a8-7cc255ec3615"
NEWER_TWIN = "000645cc-2b3a-0f00-1111-222233334444"
TWINS = [
    {"extId": NEWER_TWIN, "name": "twin", "config": {"incarnationId": 1765593061999999}},
    {"extId": OLDER_TWIN, "name": "twin", "config": {"incarnationId": 1765593061145372}},
]


def test_oldest_cluster_keeps_its_name_and_newer_ones_get_their_id() -> None:
    routing = ClusterRouting.from_clusters(TWINS, AgentMessages())

    assert (routing.host_for(OLDER_TWIN), routing.host_for(NEWER_TWIN)) == (
        "twin",
        f"twin-{NEWER_TWIN}",
    )


def test_clusters_sharing_a_name_are_reported_with_their_hosts() -> None:
    messages = AgentMessages()

    ClusterRouting.from_clusters(TWINS, messages)

    assert list(messages) == [
        ("info", f"Clusters named twin are monitored as the hosts twin, twin-{NEWER_TWIN}")
    ]


def test_cluster_without_cluster_function_is_routed_by_name() -> None:
    routing = ClusterRouting.from_clusters(
        [{"extId": "c1", "name": "cluster-a", "config": {"clusterFunction": None}}],
        AgentMessages(),
    )

    assert routing.host_for("c1") == "cluster-a"


def test_sections_are_written_to_their_hosts() -> None:
    stream = io.StringIO()

    write_sections(
        [
            Section("prism_info_v2", {"a": 1}, "cluster-a"),
            Section("prism_alerts_v2", [], None, persist_until=2000),
        ],
        stream,
        AgentMessages(),
    )

    assert stream.getvalue() == (
        "<<<prism_alerts_v2:sep(0):persist(2000)>>>\n[]\n"
        '<<<<cluster-a>>>>\n<<<prism_info_v2:sep(0)>>>\n{"a": 1}\n<<<<>>>>\n'
    )


def test_unroutable_sections_are_dropped_with_a_warning() -> None:
    stream = io.StringIO()
    messages = AgentMessages()

    write_sections(
        [Section("prism_info_v2", {}, Unroutable("unknown cluster c9"))], stream, messages
    )

    assert (stream.getvalue(), list(messages)) == (
        "",
        [("warning", "Dropped prism_info_v2: unknown cluster c9")],
    )


def test_second_section_of_a_name_on_one_host_is_dropped_with_a_warning() -> None:
    stream = io.StringIO()
    messages = AgentMessages()

    write_sections(
        [Section("prism_info_v2", 1, "cluster-a"), Section("prism_info_v2", 2, "cluster-a")],
        stream,
        messages,
    )

    assert (stream.getvalue(), list(messages)) == (
        "<<<<cluster-a>>>>\n<<<prism_info_v2:sep(0)>>>\n1\n<<<<>>>>\n",
        [("warning", "Dropped a second prism_info_v2 section for cluster-a")],
    )


@pytest.mark.parametrize(
    "fetch, warning",
    [
        pytest.param(
            _denied,
            "Could not fetch VMs: vmm/v4.0/ahv/config/vms: HTTP 403 Permission denied",
            id="API error",
        ),
        pytest.param(_buggy, "Could not fetch VMs: KeyError: 'extId'", id="bug in the fetcher"),
    ],
)
def test_failing_fetcher_loses_only_its_own_sections(
    fetch: Callable[[FetchContext], Sequence[Section]], warning: str
) -> None:
    messages = AgentMessages()

    result = run_fetchers(
        _context(),
        [Fetcher("VMs", fetch), _sections_of(Section("prism_info_v2", {}))],
        FetchSchedule(FakeStorage(), "9440-monitoring", FakeClock()),
        messages,
        debug=False,
    )

    assert (result.sections, list(messages)) == (
        [Section("prism_info_v2", {})],
        [("warning", warning)],
    )


def test_failing_fetcher_raises_in_debug_mode() -> None:
    with pytest.raises(KeyError):
        run_fetchers(
            _context(),
            [Fetcher("VMs", _buggy)],
            FetchSchedule(FakeStorage(), "9440-monitoring", FakeClock()),
            AgentMessages(),
            debug=True,
        )


def test_fetched_slow_data_is_persisted_for_two_refresh_intervals() -> None:
    schedule = FetchSchedule(FakeStorage(), "9440-monitoring", FakeClock())

    result = run_fetchers(_context(), [_slow_data()], schedule, AgentMessages(), debug=False)

    assert result.sections == [Section("prism_disks_v2", {}, persist_until=1000 + 2 * 600)]


def test_fetching_records_nothing_before_the_output_is_written() -> None:
    storage = FakeStorage()
    schedule = FetchSchedule(storage, "9440-monitoring", FakeClock())

    run_fetchers(_context(), [_slow_data()], schedule, AgentMessages(), debug=False)

    assert storage.entries == {}


def test_slow_data_is_not_fetched_again_before_it_is_due() -> None:
    clock = FakeClock()
    schedule = FetchSchedule(FakeStorage(), "9440-monitoring", clock)
    schedule.record(
        run_fetchers(_context(), [_slow_data()], schedule, AgentMessages(), debug=False).succeeded
    )
    clock.now += 60

    result = run_fetchers(_context(), [_slow_data()], schedule, AgentMessages(), debug=False)

    assert result.sections == []


def test_failed_slow_data_is_due_again_on_the_next_run() -> None:
    clock = FakeClock()
    schedule = FetchSchedule(FakeStorage(), "9440-monitoring", clock)
    failing = Fetcher("disks", _denied, timedelta(minutes=10))
    schedule.record(
        run_fetchers(_context(), [failing], schedule, AgentMessages(), debug=False).succeeded
    )
    clock.now += 60

    assert schedule.is_due(failing)


def test_v4_agent_queries_only_the_v4_api(api: responses.RequestsMock) -> None:
    api.get(v4_url(CLUSTERS_PATH), json=recorded_clusters(), match=[page_matcher(0)])

    agent_prism_main(parse_arguments(_v4_args()))

    assert [call.request.url for call in api.calls] == [
        f"{BASE_URL}/api/{CLUSTERS_PATH}?%24page=0&%24limit=100"
    ]


def test_v4_agent_without_sections_reports_it_is_not_implemented(
    api: responses.RequestsMock, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(v4_url(CLUSTERS_PATH), json=recorded_clusters(), match=[page_matcher(0)])

    exit_code = agent_prism_main(parse_arguments(_v4_args()))

    assert (exit_code, capsys.readouterr().err) == (1, "Nutanix API v4 is not implemented yet\n")


def test_v4_agent_reports_unreachable_cluster_list_in_one_line(
    api: responses.RequestsMock, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(
        v4_url(CLUSTERS_PATH),
        status=HTTPStatus.UNAUTHORIZED,
        json=LOGIN_REJECTED,
    )

    exit_code = agent_prism_main(parse_arguments(_v4_args()))

    assert (exit_code, capsys.readouterr().err) == (
        1,
        (
            "Could not fetch the clusters from Prism Central: "
            f"{CLUSTERS_PATH}: HTTP 401 invalid credentials\n"
        ),
    )
