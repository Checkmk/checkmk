# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import json
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path
from types import MappingProxyType
from urllib.parse import parse_qsl, urlsplit

import pytest
import responses
from responses import matchers

from cmk.plugins.prism.special_agent.agent_prism import agent_prism_main, parse_arguments
from cmk.plugins.prism.special_agent.agent_prism_v4 import (
    ALERTS_PATH,
    ClusterRouting,
    CLUSTERS_PATH,
    CONTAINER_STATS_PATH,
    CONTAINERS_PATH,
    fetch_alerts,
    fetch_containers,
    fetch_hosts,
    fetch_vms,
    FetchContext,
    Fetcher,
    FetchSchedule,
    HOSTS_PATH,
    run_fetchers,
    Section,
    Unroutable,
    VMS_PATH,
    write_sections,
)
from cmk.plugins.prism.special_agent.v4_client import JsonObject, PrismV4Client, PrismV4Error
from cmk.server_side_programs.v1 import AgentMessages

from .v4_testing import (
    BASE_URL,
    FakeStorage,
    LOGIN_REJECTED,
    page,
    page_matcher,
    PASSWORD,
    SERVER,
    USERNAME,
    v4_url,
)

FIXTURES = Path(__file__).parent / "v4_fixtures"


def _recorded(name: str) -> dict[str, object]:
    loaded: dict[str, object] = json.loads((FIXTURES / name).read_text())
    return loaded


def recorded_clusters() -> dict[str, object]:
    """The cluster list of a Prism Central 7.5 lab (anonymised): one cluster and PC itself"""
    return _recorded("clustermgmt_config_clusters.json")


def recorded_hosts() -> dict[str, object]:
    """The host list of the same lab: the three hosts of cluster-a"""
    return _recorded("clustermgmt_config_hosts.json")


def recorded_alerts() -> dict[str, object]:
    """Open alerts of the same lab: three on Prism Central, one on cluster-a"""
    return _recorded("monitoring_serviceability_alerts.json")


# Three of the lab's containers (anonymised), by extId: one with dedup savings, the default
# container and an internal one
RECORDED_CONTAINERS = {
    "17aa3706-6394-405c-ae6a-964d9cb64aa2": "NutanixManagementShare",
    "58973d0f-3460-49fa-9c29-e94958c51fa8": "default",
    "e2f3f2fe-7738-4399-a8ce-1deebbefe62c": "container-dedup",
}


# The data of a recorded stats response: each field's samples
type Stats = dict[str, list[dict[str, object]]]


def _keep(_stats: Stats) -> None:
    pass


def _serve_recorded_containers(
    api: responses.RequestsMock,
    statuses: Mapping[str, HTTPStatus] = MappingProxyType({}),
    edit_dedup_stats: Callable[[Stats], None] = _keep,
) -> None:
    """The stats of a container can be answered with an error, those of container-dedup edited"""
    api.get(
        v4_url(CONTAINERS_PATH),
        json=json.loads((FIXTURES / "clustermgmt_config_storage_containers.json").read_text()),
        match=[
            page_matcher(0),
            matchers.query_param_matcher(
                {"$select": "containerExtId,name,clusterExtId,cacheDeduplication"},
                strict_match=False,
            ),
        ],
    )
    for ext_id, name in RECORDED_CONTAINERS.items():
        stats = json.loads(
            (FIXTURES / f"clustermgmt_stats_storage_containers_{name}.json").read_text()
        )
        if (status := statuses.get(name, HTTPStatus.OK)) is not HTTPStatus.OK:
            api.get(
                v4_url(f"{CONTAINER_STATS_PATH}/{ext_id}"),
                status=status,
                json={"message": status.phrase},
            )
            continue
        if name == "container-dedup":
            edit_dedup_stats(stats["data"])
        api.get(v4_url(f"{CONTAINER_STATS_PATH}/{ext_id}"), json=stats)


def _serve_recorded_vms(api: responses.RequestsMock) -> None:
    """The 161 VMs of the lab (anonymised) on two pages"""
    for page_number in (0, 1):
        api.get(
            v4_url(VMS_PATH),
            json=_recorded(f"vmm_ahv_config_vms_page{page_number}.json"),
            match=[page_matcher(page_number)],
        )


def _recorded_host_list() -> list[JsonObject]:
    """The hosts of the lab (anonymised), as agent_prism_v4_main lists them"""
    assert isinstance(hosts := recorded_hosts()["data"], list)
    return hosts


def _container_names_and_messages(
    sections: Sequence[Section], messages: AgentMessages
) -> tuple[list[object], list[tuple[str, str]]]:
    assert isinstance(containers := sections[0].payload, list)
    return [c["name"] for c in containers], list(messages)


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


def _context(
    messages: AgentMessages | None = None,
    hosts: Sequence[JsonObject] | PrismV4Error = (),
) -> FetchContext:
    client = PrismV4Client(
        BASE_URL,
        USERNAME,
        PASSWORD,
        True,
        timeout=10,
        deadline=time.monotonic() + 60,
    )
    return FetchContext(
        client, [], _routing(), AgentMessages() if messages is None else messages, hosts
    )


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


def test_hosts_go_to_their_cluster_with_only_the_checked_fields() -> None:
    assert fetch_hosts(_context(hosts=_recorded_host_list())) == [
        Section(
            "prism_hosts_v2",
            [
                {
                    "hostName": f"host-{number}",
                    "nodeStatus": "NORMAL",
                    "memorySizeBytes": 1622495199232,
                    "bootTimeUsecs": boot_time,
                    "hypervisor": {"numberOfVms": vms, "acropolisConnectionState": "CONNECTED"},
                }
                for number, vms, boot_time in [
                    (3, 54, 1780720908550400),
                    (1, 30, 1780730564446688),
                    (2, 42, 1780725763871836),
                ]
            ],
            "cluster-a",
        )
    ]


def test_hosts_without_a_cluster_are_not_routed() -> None:
    assert [
        section.target for section in fetch_hosts(_context(hosts=[{"hostName": "host-1"}]))
    ] == [Unroutable("hosts without a cluster")]


def test_failed_host_listing_is_reported_by_the_hosts_fetcher() -> None:
    error = PrismV4Error("clustermgmt/v4.0/config/hosts: HTTP 403 Permission denied")

    with pytest.raises(PrismV4Error) as raised:
        fetch_hosts(_context(hosts=error))

    assert raised.value is error


def _alerts_by_target(sections: Sequence[Section]) -> dict[object, list[object]]:
    by_target: dict[object, list[object]] = {}
    for section in sections:
        assert section.name == "prism_alerts_v2"
        assert isinstance(section.payload, list)
        by_target[section.target] = [alert["message"] for alert in section.payload]
    return by_target


def test_alerts_go_to_their_cluster_or_prism_central(api: responses.RequestsMock) -> None:
    api.get(v4_url(ALERTS_PATH), json=recorded_alerts(), match=[page_matcher(0)])

    assert _alerts_by_target(fetch_alerts(_context())) == {
        None: [
            (
                "Disk space usage for {mount_path} on {entity} {ip_address} has exceeded "
                "{threshold}%. {ref_msg}"
            ),
            "{alert_msg}",
            "Fileserver not reachable from PC",
        ],
        "cluster-a": ["Host {hypervisor_address} appears to have failed. {failover_host_info}"],
    }


def _sent_query(api: responses.RequestsMock) -> dict[str, str]:
    return dict(parse_qsl(urlsplit(api.calls[0].request.url or "").query))


def test_alerts_are_fetched_unresolved_and_unacknowledged_only(
    api: responses.RequestsMock,
) -> None:
    api.get(v4_url(ALERTS_PATH), json=page([], has_next=False), match=[page_matcher(0)])

    fetch_alerts(_context())

    assert _sent_query(api)["$filter"] == ("isResolved eq false and isAcknowledged eq false")


def test_alerts_are_fetched_with_only_the_checked_fields(api: responses.RequestsMock) -> None:
    api.get(v4_url(ALERTS_PATH), json=page([], has_next=False), match=[page_matcher(0)])

    fetch_alerts(_context())

    assert set(_sent_query(api)["$select"].split(",")) == {
        "severity",
        "message",
        "creationTime",
        "parameters",
        "clusterUUID",
        "sourceEntity",
    }


def test_cluster_without_alerts_gets_an_empty_section(api: responses.RequestsMock) -> None:
    api.get(v4_url(ALERTS_PATH), json=page([], has_next=False), match=[page_matcher(0)])

    assert _alerts_by_target(fetch_alerts(_context())) == {None: [], "cluster-a": []}


def test_prism_central_gets_an_alerts_section_even_if_not_listed_as_cluster(
    api: responses.RequestsMock,
) -> None:
    api.get(v4_url(ALERTS_PATH), json=page([], has_next=False), match=[page_matcher(0)])
    context = FetchContext(_context().client, [], ClusterRouting({}), AgentMessages())

    assert fetch_alerts(context) == [Section("prism_alerts_v2", [], None)]


def test_alert_keeps_only_the_checked_fields(api: responses.RequestsMock) -> None:
    alert = {
        "extId": "a1",
        "clusterUUID": CLUSTER_ID,
        "isResolved": False,
        "title": "Host failed",
        "severity": "CRITICAL",
        "message": "Host {host} failed",
        "creationTime": "2026-08-11T19:48:53.264196Z",
        "sourceEntity": {"type": "node", "name": "host-1", "extId": "h1"},
        "parameters": [
            {
                "$objectType": "monitoring.v4.common.Parameter",
                "paramName": "host",
                "paramValue": {
                    "$objectType": "monitoring.v4.common.StringValue",
                    "stringValue": "host-1",
                },
            }
        ],
    }
    api.get(v4_url(ALERTS_PATH), json=page([alert], has_next=False), match=[page_matcher(0)])

    sections = {section.target: section.payload for section in fetch_alerts(_context())}

    assert sections["cluster-a"] == [
        {
            "severity": "CRITICAL",
            "message": "Host {host} failed",
            "creationTime": "2026-08-11T19:48:53.264196Z",
            "parameters": [{"paramName": "host", "paramValue": {"stringValue": "host-1"}}],
            "sourceEntity": {"type": "node"},
        }
    ]


def test_alerts_without_a_cluster_are_not_routed(api: responses.RequestsMock) -> None:
    alert = {"severity": "INFO", "message": "m", "creationTime": "2026-08-11T19:48:53Z"}
    api.get(v4_url(ALERTS_PATH), json=page([alert], has_next=False), match=[page_matcher(0)])

    assert Unroutable("alerts without a cluster") in [
        section.target for section in fetch_alerts(_context())
    ]


def test_v4_agent_queries_only_the_v4_api(api: responses.RequestsMock) -> None:
    api.get(v4_url(CLUSTERS_PATH), json=recorded_clusters(), match=[page_matcher(0)])
    api.get(v4_url(HOSTS_PATH), json=recorded_hosts(), match=[page_matcher(0)])
    api.get(v4_url(ALERTS_PATH), json=recorded_alerts(), match=[page_matcher(0)])
    _serve_recorded_containers(api)
    _serve_recorded_vms(api)

    agent_prism_main(parse_arguments(_v4_args()))

    assert sorted(call.request.path_url.split("?")[0] for call in api.calls) == sorted(
        f"/api/{path}"
        for path in (
            CLUSTERS_PATH,
            HOSTS_PATH,
            ALERTS_PATH,
            CONTAINERS_PATH,
            *(f"{CONTAINER_STATS_PATH}/{ext_id}" for ext_id in RECORDED_CONTAINERS),
            # Two pages
            VMS_PATH,
            VMS_PATH,
        )
    )


def test_containers_section_holds_the_monitored_series_per_cluster(
    api: responses.RequestsMock,
) -> None:
    """Each series keeps all samples of the window, the parse function picks the newest"""
    _serve_recorded_containers(api)

    sections = fetch_containers(_context())

    assert sections == [
        Section(
            "prism_containers_v2",
            json.loads((FIXTURES / "section_prism_containers_v2.json").read_text()),
            "cluster-a",
        )
    ]


def test_container_that_no_longer_exists_is_left_out_silently(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_containers(api, statuses={"container-dedup": HTTPStatus.NOT_FOUND})
    messages = AgentMessages()

    sections = fetch_containers(_context(messages))

    assert _container_names_and_messages(sections, messages) == (
        ["NutanixManagementShare", "default"],
        [],
    )


def test_container_stats_error_other_than_not_found_fails_the_fetcher(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_containers(api, statuses={"container-dedup": HTTPStatus.FORBIDDEN})

    with pytest.raises(PrismV4Error):
        fetch_containers(_context())


def test_failing_first_container_stats_call_stops_the_fetcher_before_the_others(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_containers(api, statuses={"NutanixManagementShare": HTTPStatus.FORBIDDEN})
    # The stats of the other containers are what must not be fetched
    api.assert_all_requests_are_fired = False

    with pytest.raises(PrismV4Error):
        fetch_containers(_context())

    assert [
        (call.request.url or "").split("?")[0]
        for call in api.calls
        if CONTAINER_STATS_PATH in (call.request.url or "")
    ] == [v4_url(f"{CONTAINER_STATS_PATH}/17aa3706-6394-405c-ae6a-964d9cb64aa2")]


def test_stats_of_no_container_found_fails_the_fetcher(api: responses.RequestsMock) -> None:
    _serve_recorded_containers(
        api, statuses=dict.fromkeys(RECORDED_CONTAINERS.values(), HTTPStatus.NOT_FOUND)
    )

    with pytest.raises(PrismV4Error):
        fetch_containers(_context())


def _drop_replication_factor(stats: Stats) -> None:
    stats["storageReplicationFactor"] = []


def _zero_replication_factor(stats: Stats) -> None:
    for sample in stats["storageReplicationFactor"]:
        sample["value"] = 0


@pytest.mark.parametrize("edit", [_drop_replication_factor, _zero_replication_factor])
def test_container_without_usage_stats_is_skipped_with_an_info(
    api: responses.RequestsMock, edit: Callable[[Stats], None]
) -> None:
    _serve_recorded_containers(api, edit_dedup_stats=edit)
    messages = AgentMessages()

    sections = fetch_containers(_context(messages))

    assert _container_names_and_messages(sections, messages) == (
        ["NutanixManagementShare", "default"],
        [
            (
                "info",
                (
                    "Skipped storage container 'container-dedup': "
                    "Prism Central has no usage stats for it"
                ),
            )
        ],
    )


@pytest.mark.parametrize(
    ["broken", "message"],
    [
        pytest.param(
            {"name": "broken"},
            "Skipped storage container 'broken': "
            "Prism Central reports no valid containerExtId, clusterExtId for it",
            id="named",
        ),
        pytest.param(
            {},
            "Skipped a storage container without a name: "
            "Prism Central reports no valid containerExtId, name, clusterExtId for it",
            id="unnamed",
        ),
    ],
)
def test_container_that_does_not_fit_the_model_is_skipped_with_an_info(
    api: responses.RequestsMock, broken: dict[str, object], message: str
) -> None:
    recorded = _recorded("clustermgmt_config_storage_containers.json")
    assert isinstance(listed := recorded["data"], list)
    default = next(container for container in listed if container["name"] == "default")
    api.get(
        v4_url(CONTAINERS_PATH),
        json=page([broken, default], has_next=False),
        match=[page_matcher(0)],
    )
    api.get(
        v4_url(f"{CONTAINER_STATS_PATH}/{default['containerExtId']}"),
        json=_recorded("clustermgmt_stats_storage_containers_default.json"),
    )
    messages = AgentMessages()

    sections = fetch_containers(_context(messages))

    assert _container_names_and_messages(sections, messages) == (["default"], [("info", message)])


@pytest.mark.parametrize("value", [None, 58284175018156.0, True])
def test_container_sample_without_an_integer_is_left_out(
    api: responses.RequestsMock, value: object
) -> None:
    def replace_newest_capacity(stats: Stats) -> None:
        stats["storageCapacityBytes"][0]["value"] = value

    _serve_recorded_containers(api, edit_dedup_stats=replace_newest_capacity)

    sections = fetch_containers(_context())

    assert isinstance(containers := sections[0].payload, list)
    assert [sample["timestamp"] for sample in containers[2]["stats"]["storageCapacityBytes"]] == [
        f"2026-10-28T{hour:02d}:00:00Z" for hour in range(14, 3, -1)
    ]


def test_vms_section_holds_only_the_monitored_fields_per_cluster(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_vms(api)

    sections = fetch_vms(_context(hosts=_recorded_host_list()))

    assert sections == [
        Section(
            "prism_vms_v2",
            json.loads((FIXTURES / "section_prism_vms_v2.json").read_text()),
            "cluster-a",
        )
    ]


def test_vms_are_reported_without_host_names_if_the_host_listing_failed(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_vms(api)

    sections = fetch_vms(_context(hosts=PrismV4Error("clustermgmt/v4.0/config/hosts: timed out")))

    assert isinstance(vms := sections[0].payload, list)
    assert (len(vms), [vm["name"] for vm in vms if "hostName" in vm]) == (161, [])


def test_vm_that_does_not_fit_the_model_is_skipped_with_an_info(
    api: responses.RequestsMock,
) -> None:
    recorded = _recorded("vmm_ahv_config_vms_page0.json")
    assert isinstance(listed := recorded["data"], list)
    api.get(
        v4_url(VMS_PATH),
        json=page([{"name": "broken", "powerState": "ON"}, listed[0]], has_next=False),
        match=[page_matcher(0)],
    )
    messages = AgentMessages()

    sections = fetch_vms(_context(messages, _recorded_host_list()))

    assert isinstance(vms := sections[0].payload, list)
    assert ([vm["name"] for vm in vms], list(messages)) == (
        ["vm-001"],
        [
            (
                "info",
                (
                    "Skipped VM 'broken': Prism Central reports no valid "
                    "extId, memorySizeBytes, cluster for it"
                ),
            )
        ],
    )


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
