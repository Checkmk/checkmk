# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from types import MappingProxyType
from urllib.parse import parse_qsl, urlsplit

import pytest
import responses
from pydantic import ValidationError
from responses import matchers

from cmk.plugins.prism.special_agent.agent_prism import agent_prism_main, parse_arguments
from cmk.plugins.prism.special_agent.agent_prism_v4 import (
    AHV_VM_STATS_PATH,
    AHV_VMS_PATH,
    ALERTS_PATH,
    CLUSTER_STATS_PATH,
    ClusterRouting,
    CLUSTERS_PATH,
    CONTAINER_STATS_PATH,
    CONTAINERS_PATH,
    DISK_STATS_PATH,
    DISKS_PATH,
    ESXI_VM_STATS_PATH,
    ESXI_VMS_PATH,
    fetch_alerts,
    fetch_clusters,
    fetch_containers,
    fetch_ha,
    fetch_host_nics,
    fetch_hosts,
    fetch_nodes,
    fetch_remote_support,
    fetch_storage_pools,
    fetch_vms,
    FetchContext,
    Fetcher,
    FetchSchedule,
    HOST_NICS_PATH,
    HOSTS_PATH,
    run_fetchers,
    Section,
    Unroutable,
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


def _serve_recorded_vms(
    api: responses.RequestsMock,
    esxi_vms: Sequence[object] | None = None,
    esxi_vm_stats: Sequence[object] = (),
) -> None:
    """The 161 AHV VMs of the lab (anonymised) on two pages. The lab has no ESXi VMs unless
    given."""
    for page_number in (0, 1):
        api.get(
            v4_url(AHV_VMS_PATH),
            json=_recorded(f"vmm_ahv_config_vms_page{page_number}.json"),
            match=[page_matcher(page_number)],
        )
    api.get(
        v4_url(ESXI_VMS_PATH),
        json=_recorded("vmm_esxi_config_vms.json")
        if esxi_vms is None
        else page(esxi_vms, has_next=False),
        match=[page_matcher(0)],
    )
    _serve_recorded_vm_stats(api)
    if esxi_vms is not None:
        api.get(v4_url(ESXI_VM_STATS_PATH), json=page(esxi_vm_stats, has_next=False))


def _serve_recorded_vm_stats(api: responses.RequestsMock) -> None:
    """The stats of the AHV VMs and of the 3 CVMs of the lab, one sample each"""
    for page_number in (0, 1):
        api.get(
            v4_url(AHV_VM_STATS_PATH),
            json=_recorded(f"vmm_ahv_stats_vms_page{page_number}.json"),
            match=[page_matcher(page_number)],
        )


def _vm_sections(sections: Sequence[Section]) -> dict[object, object]:
    return {
        section.target: section.payload for section in sections if section.name == "prism_vm_v2"
    }


def _recorded_host_list() -> list[JsonObject]:
    """The hosts of the lab (anonymised), as agent_prism_v4_main lists them"""
    assert isinstance(hosts := recorded_hosts()["data"], list)
    return hosts


# The hosts of recorded_hosts() by extId, with the host and disk stats of the same lab
RECORDED_NODES = {
    "247a477f-b32f-4fc1-83a6-c73172169e73": "host-3",
    "24bce4ff-ea77-4f52-84b2-438552e227be": "host-1",
    "387a54c1-7286-49aa-9602-a7e8e889f63c": "host-2",
}
HOST_STATS_FIELDS = (
    "controllerAvgIoLatencyUsecs,controllerAvgReadIoLatencyUsecs,"
    "controllerAvgWriteIoLatencyUsecs,controllerReadIoBandwidthKbps,"
    "controllerWriteIoBandwidthKbps,controllerNumReadIops,controllerNumWriteIops,"
    "hypervisorCpuUsagePpm,cpuCapacityHz,aggregateHypervisorMemoryUsagePpm,"
    "storageCapacityBytes,freePhysicalStorageBytes"
)


def _host_stats_path(host_id: str) -> str:
    return f"clustermgmt/v4.0/stats/clusters/{CLUSTER_ID}/hosts/{host_id}"


def _serve_recorded_nodes(
    api: responses.RequestsMock,
    statuses: Mapping[str, HTTPStatus] = MappingProxyType({}),
) -> None:
    """The stats of a host or disk (by extId) can be answered with an error"""
    for host_id, response in _recorded("clustermgmt_stats_hosts.json").items():
        _serve_stats(
            api,
            _host_stats_path(host_id),
            response,
            statuses.get(host_id, HTTPStatus.OK),
            {"$select": HOST_STATS_FIELDS, "$samplingInterval": "30"},
        )
    _serve_recorded_disks(api, statuses)


def _serve_recorded_disks(
    api: responses.RequestsMock,
    statuses: Mapping[str, HTTPStatus] = MappingProxyType({}),
) -> None:
    """The stats of a disk (by extId) can be answered with an error"""
    api.get(
        v4_url(DISKS_PATH),
        json=_recorded("clustermgmt_config_disks.json"),
        match=[
            page_matcher(0),
            matchers.query_param_matcher(
                {
                    "$select": "location,model,serialNumber,storageTier,diskAdvanceConfig,"
                    "extId,nodeExtId,storagePoolExtId,clusterExtId"
                },
                strict_match=False,
            ),
        ],
    )
    for disk_id, response in _recorded("clustermgmt_stats_disks.json").items():
        _serve_stats(
            api,
            f"{DISK_STATS_PATH}/{disk_id}",
            response,
            statuses.get(disk_id, HTTPStatus.OK),
            {"$samplingInterval": "30"},
        )


def _serve_stats(
    api: responses.RequestsMock,
    path: str,
    response: object,
    status: HTTPStatus,
    query: dict[str, str],
) -> None:
    if status is not HTTPStatus.OK:
        api.get(v4_url(path), status=status, json={"message": status.phrase})
        return
    api.get(
        v4_url(path),
        json=response,
        match=[matchers.query_param_matcher(query, strict_match=False)],
    )


def _container_names_and_messages(
    sections: Sequence[Section], messages: AgentMessages
) -> tuple[list[object], list[tuple[str, str]]]:
    assert isinstance(containers := sections[0].payload, list)
    return [c["name"] for c in containers], list(messages)


CLUSTER_ID = "000645cc-2b3a-3b1c-06a8-7cc255ec3615"
PRISM_CENTRAL_ID = "0806a141-8916-471b-99fd-b5119ff280ef"
CLUSTER_HOST = "cluster-a_55ec3615"


def _serve_cluster_stats(api: responses.RequestsMock, status: HTTPStatus = HTTPStatus.OK) -> None:
    """The stats of cluster-a, or an error instead"""
    _serve_stats(
        api,
        f"{CLUSTER_STATS_PATH}/{CLUSTER_ID}",
        _recorded("clustermgmt_stats_clusters_cluster-a.json"),
        status,
        {"$samplingInterval": "30"},
    )


def _cluster_section(name: str) -> dict[str, object]:
    """What the v4 agent writes for a cluster of the lab"""
    return _recorded(f"section_prism_info_v2_{name}.json")


def _cluster_section_without_stats(name: str) -> dict[str, object]:
    return {key: value for key, value in _cluster_section(name).items() if key != "stats"}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _recorded_cluster_list() -> list[JsonObject]:
    clusters = recorded_clusters()["data"]
    assert isinstance(clusters, list)
    return clusters


def _routing() -> ClusterRouting:
    return ClusterRouting.from_clusters(_recorded_cluster_list())


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
    assert _routing().host_for(CLUSTER_ID) == CLUSTER_HOST


def test_prism_central_data_stays_on_prism_central_host() -> None:
    assert _routing().host_for(PRISM_CENTRAL_ID) is None


def test_unknown_cluster_is_not_routed() -> None:
    assert _routing().host_for("c-unknown") == Unroutable("unknown cluster c-unknown")


# Real extIds start with the creation time, so clusters created together share a long prefix.
TWIN_A = "000645cc-2b3a-3b1c-06a8-7cc255ec3615"
TWIN_B = "000645cc-2b3a-0f00-1111-222233334444"


def test_clusters_sharing_a_name_get_a_host_each() -> None:
    routing = ClusterRouting.from_clusters(
        [{"extId": TWIN_A, "name": "twin"}, {"extId": TWIN_B, "name": "twin"}]
    )

    assert (routing.host_for(TWIN_A), routing.host_for(TWIN_B)) == (
        "twin_55ec3615",
        "twin_33334444",
    )


def test_cluster_without_a_name_is_routed_by_its_id() -> None:
    routing = ClusterRouting.from_clusters([{"extId": TWIN_A, "name": None}])

    assert routing.host_for(TWIN_A) == TWIN_A


def test_cluster_without_cluster_function_gets_a_cluster_host() -> None:
    routing = ClusterRouting.from_clusters(
        [{"extId": TWIN_A, "name": "cluster-a", "config": {"clusterFunction": None}}]
    )

    assert routing.host_for(TWIN_A) == "cluster-a_55ec3615"


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
            CLUSTER_HOST,
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


def test_hypervisors_go_to_their_cluster_for_the_ha_state() -> None:
    assert fetch_ha(_context(hosts=_recorded_host_list())) == [
        Section("prism_ha_v2", _recorded("section_prism_ha_v2.json"), CLUSTER_HOST)
    ]


def test_hypervisors_without_a_cluster_are_not_routed() -> None:
    assert [section.target for section in fetch_ha(_context(hosts=[{"hostName": "host-1"}]))] == [
        Unroutable("hosts without a cluster")
    ]


def test_failed_host_listing_is_reported_by_the_ha_fetcher() -> None:
    error = PrismV4Error("clustermgmt/v4.0/config/hosts: HTTP 403 Permission denied")

    with pytest.raises(PrismV4Error) as raised:
        fetch_ha(_context(hosts=error))

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
        CLUSTER_HOST: ["Host {hypervisor_address} appears to have failed. {failover_host_info}"],
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

    assert _alerts_by_target(fetch_alerts(_context())) == {None: [], CLUSTER_HOST: []}


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

    assert sections[CLUSTER_HOST] == [
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
    _serve_recorded_nodes(api)
    _serve_recorded_host_nics(api)
    _serve_cluster_stats(api)

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
            AHV_VMS_PATH,
            AHV_VMS_PATH,
            ESXI_VMS_PATH,
            DISKS_PATH,
            *(_host_stats_path(ext_id) for ext_id in RECORDED_NODES),
            *(
                f"{DISK_STATS_PATH}/{ext_id}"
                for ext_id in _recorded("clustermgmt_stats_disks.json")
            ),
            # Two pages, the next link of the second is past the total
            AHV_VM_STATS_PATH,
            AHV_VM_STATS_PATH,
            HOST_NICS_PATH,
            f"{CLUSTER_STATS_PATH}/{CLUSTER_ID}",
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
            CLUSTER_HOST,
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

    assert [section for section in sections if section.name == "prism_vms_v2"] == [
        Section(
            "prism_vms_v2",
            json.loads((FIXTURES / "section_prism_vms_v2.json").read_text()),
            CLUSTER_HOST,
        )
    ]


def test_each_vm_gets_a_section_on_a_piggyback_host_of_its_own(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_vms(api)

    targets = _vm_sections(fetch_vms(_context(hosts=_recorded_host_list())))

    # The CVMs in the stats list get none, vm-119 is the name of two VMs
    assert (len(targets), [t for t in targets if str(t).startswith("vm-119_")]) == (
        161,
        ["vm-119_f9d9ed69", "vm-119_5fcd68a4"],
    )


def test_vm_section_holds_the_config_and_the_stats_of_the_vm(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_vms(api)

    vms = _vm_sections(fetch_vms(_context(hosts=_recorded_host_list())))

    assert vms["vm-006_a725d6c8"] == {
        "extId": "a725d6c8-92eb-4cb3-4ffe-02cba4f8848a",
        "name": "vm-006",
        "hypervisor": "AHV",
        "powerState": "ON",
        "hostName": "host-2",
        "numVcpus": 4,
        "memorySizeBytes": 8589934592,
        "protectionType": "UNPROTECTED",
        "guestTools": {"version": "4.5", "isInstalled": True, "isEnabled": True},
        "stats": [
            {
                "timestamp": "2026-11-04T15:00:00Z",
                "controllerAvgIoLatencyMicros": 1784,
                "controllerAvgReadIoLatencyMicros": 0,
                "controllerAvgWriteIoLatencyMicros": 1784,
                "controllerAvgReadIoSizeKb": 0,
                "controllerAvgWriteIoSizeKb": 12,
                "hypervisorCpuUsagePpm": 1254,
                "hypervisorCpuReadyTimePpm": 3,
                "guestMemoryUsagePpm": 879062,
            }
        ],
    }


@pytest.mark.parametrize(
    ["status", "expected_message"],
    [
        pytest.param(
            HTTPStatus.NOT_FOUND,
            ("info", f"Could not fetch the AHV VM stats: {AHV_VM_STATS_PATH}: HTTP 404 Not Found"),
            id="no stats API",
        ),
        pytest.param(
            HTTPStatus.FORBIDDEN,
            (
                "warning",
                f"Could not fetch the AHV VM stats: {AHV_VM_STATS_PATH}: HTTP 403 Forbidden",
            ),
            id="any other error",
        ),
    ],
)
def test_vms_are_reported_without_stats_if_the_stats_cannot_be_listed(
    api: responses.RequestsMock, status: HTTPStatus, expected_message: tuple[str, str]
) -> None:
    for page_number in (0, 1):
        api.get(
            v4_url(AHV_VMS_PATH),
            json=_recorded(f"vmm_ahv_config_vms_page{page_number}.json"),
            match=[page_matcher(page_number)],
        )
    api.get(
        v4_url(ESXI_VMS_PATH), json=_recorded("vmm_esxi_config_vms.json"), match=[page_matcher(0)]
    )
    api.get(v4_url(AHV_VM_STATS_PATH), status=status, json={"message": status.phrase})
    messages = AgentMessages()

    vms = _vm_sections(fetch_vms(_context(messages, _recorded_host_list())))

    with_stats = [target for target, vm in vms.items() if isinstance(vm, dict) and "stats" in vm]
    assert (len(vms), with_stats, list(messages)) == (
        161,
        [],
        [expected_message],
    )


def test_vms_are_reported_without_host_names_if_the_host_listing_failed(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_vms(api)

    sections = fetch_vms(_context(hosts=PrismV4Error("clustermgmt/v4.0/config/hosts: timed out")))

    assert isinstance(vms := sections[0].payload, list)
    assert (len(vms), [vm["name"] for vm in vms if "hostName" in vm]) == (161, [])


# An ESXi VM as the v4 API reference describes it (vmm.v4.esxi.config.Vm), neither lab has one
ESXI_VM = {
    "$objectType": "vmm.v4.esxi.config.Vm",
    "extId": "50293f5e-6c41-4a2b-9d3e-0f8b7c2a1d64",
    "name": "esxi-vm",
    "description": "description of esxi-vm",
    "memorySizeBytes": 8589934592,
    "host": {
        "$objectType": "vmm.v4.esxi.config.HostReference",
        "extId": "247a477f-b32f-4fc1-83a6-c73172169e73",
    },
    "cluster": {"$objectType": "vmm.v4.esxi.config.ClusterReference", "extId": CLUSTER_ID},
    "powerState": "SUSPENDED",
}


def test_esxi_vm_gets_a_section_without_memory_stats(api: responses.RequestsMock) -> None:
    _serve_recorded_vms(
        api,
        esxi_vms=[{**ESXI_VM, "numCpus": 2}],
        esxi_vm_stats=[{"extId": ESXI_VM["extId"], "stats": []}],
    )

    vms = _vm_sections(fetch_vms(_context(hosts=_recorded_host_list())))

    assert vms["esxi-vm_50293f5e"] == {
        "extId": "50293f5e-6c41-4a2b-9d3e-0f8b7c2a1d64",
        "name": "esxi-vm",
        "hypervisor": "ESXI",
        "powerState": "SUSPENDED",
        "hostName": "host-3",
        "numVcpus": 2,
        "memorySizeBytes": 8589934592,
        "stats": [],
    }


def test_vm_missing_from_the_stats_list_gets_no_stats(api: responses.RequestsMock) -> None:
    _serve_recorded_vms(api, esxi_vms=[ESXI_VM])

    vms = _vm_sections(fetch_vms(_context(hosts=_recorded_host_list())))

    assert isinstance(vm := vms["esxi-vm_50293f5e"], dict)
    assert "stats" not in vm


def test_esxi_vms_are_reported_with_the_ahv_vms(api: responses.RequestsMock) -> None:
    _serve_recorded_vms(api, esxi_vms=[ESXI_VM])

    sections = fetch_vms(_context(hosts=_recorded_host_list()))

    assert isinstance(vms := sections[0].payload, list)
    assert (len(vms), vms[-1]) == (
        162,
        {
            "extId": "50293f5e-6c41-4a2b-9d3e-0f8b7c2a1d64",
            "name": "esxi-vm",
            "powerState": "SUSPENDED",
            "description": "description of esxi-vm",
            "memorySizeBytes": 8589934592,
            "hostName": "host-3",
        },
    )


@pytest.mark.parametrize(
    ["status", "expected_message"],
    [
        pytest.param(
            HTTPStatus.NOT_FOUND,
            ("info", f"Could not fetch the ESXi VMs: {ESXI_VMS_PATH}: HTTP 404 Not Found"),
            id="no ESXi API",
        ),
        pytest.param(
            HTTPStatus.FORBIDDEN,
            ("warning", f"Could not fetch the ESXi VMs: {ESXI_VMS_PATH}: HTTP 403 Forbidden"),
            id="any other error",
        ),
    ],
)
def test_ahv_vms_are_reported_if_the_esxi_vms_cannot_be_listed(
    api: responses.RequestsMock, status: HTTPStatus, expected_message: tuple[str, str]
) -> None:
    for page_number in (0, 1):
        api.get(
            v4_url(AHV_VMS_PATH),
            json=_recorded(f"vmm_ahv_config_vms_page{page_number}.json"),
            match=[page_matcher(page_number)],
        )
    api.get(v4_url(ESXI_VMS_PATH), status=status, json={"message": status.phrase})
    _serve_recorded_vm_stats(api)
    messages = AgentMessages()

    sections = fetch_vms(_context(messages))

    assert isinstance(vms := sections[0].payload, list)
    assert (len(vms), list(messages)) == (161, [expected_message])


def test_vm_that_does_not_fit_the_model_is_skipped_with_an_info(
    api: responses.RequestsMock,
) -> None:
    recorded = _recorded("vmm_ahv_config_vms_page0.json")
    assert isinstance(listed := recorded["data"], list)
    api.get(
        v4_url(AHV_VMS_PATH),
        json=page([{"name": "broken", "powerState": "ON"}, listed[0]], has_next=False),
        match=[page_matcher(0)],
    )
    api.get(
        v4_url(ESXI_VMS_PATH), json=_recorded("vmm_esxi_config_vms.json"), match=[page_matcher(0)]
    )
    _serve_recorded_vm_stats(api)
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


def _remote_support_sections(clusters: Sequence[JsonObject]) -> Sequence[Section]:
    routing = ClusterRouting.from_clusters(clusters)
    return fetch_remote_support(FetchContext(_context().client, clusters, routing, AgentMessages()))


def _with_remote_support(cluster: JsonObject, enabled: bool) -> JsonObject:
    assert isinstance(config := cluster["config"], dict)
    return {**cluster, "config": {**config, "isRemoteSupportEnabled": enabled}}


def test_remote_support_goes_to_its_cluster_or_prism_central_with_only_the_checked_field() -> None:
    # Remote support is off on the whole lab, so cluster-a's is switched on
    clusters = [
        _with_remote_support(cluster, cluster["extId"] == CLUSTER_ID)
        for cluster in _recorded_cluster_list()
    ]

    sections = _remote_support_sections(clusters)

    assert sections == [
        Section(
            "prism_remote_support_v2", {"config": {"isRemoteSupportEnabled": True}}, CLUSTER_HOST
        ),
        Section("prism_remote_support_v2", {"config": {"isRemoteSupportEnabled": False}}, None),
    ]


def test_remote_support_of_a_cluster_without_an_id_is_not_routed() -> None:
    cluster = {"name": "cluster-a", "config": {"isRemoteSupportEnabled": False}}

    sections = _remote_support_sections([cluster])

    assert [section.target for section in sections] == [Unroutable("clusters without an ID")]


def test_cluster_without_a_remote_support_state_fails_the_fetcher() -> None:
    cluster = {"extId": CLUSTER_ID, "name": "cluster-a", "config": {}}

    with pytest.raises(ValidationError):
        _remote_support_sections([cluster])


def _payload_of(host: str, sections: Sequence[Section]) -> object:
    return next(section.payload for section in sections if section.target == host)


def _disk_stats_of(section: Section) -> list[object]:
    assert isinstance(section.payload, dict)
    return [disk["stats"] for disk in section.payload["disks"]]


def _disk_serials(section: Section) -> list[str]:
    assert isinstance(section.payload, dict)
    return sorted(disk["config"]["serialNumber"] for disk in section.payload["disks"])


def test_each_node_goes_to_a_host_of_its_name_with_only_the_checked_fields(
    api: responses.RequestsMock,
) -> None:
    """Each series keeps all samples of the window, the parse function picks the newest"""
    _serve_recorded_nodes(api)

    sections = fetch_nodes(_context(hosts=_recorded_host_list()))

    assert [(section.name, section.target) for section in sections] == [
        ("prism_host_v2", "host-3"),
        ("prism_host_v2", "host-1"),
        ("prism_host_v2", "host-2"),
    ]
    assert _payload_of("host-2", sections) == _recorded("section_prism_host_v2.json")


def test_node_gets_the_disks_of_its_own(api: responses.RequestsMock) -> None:
    _serve_recorded_nodes(api)

    assert {
        section.target: _disk_serials(section)
        for section in fetch_nodes(_context(hosts=_recorded_host_list()))
    } == {
        host: [f"DISKSERIAL{number:02d}" for number in range(first, first + 6)]
        for host, first in (("host-3", 1), ("host-1", 7), ("host-2", 13))
    }


HOST_1 = "24bce4ff-ea77-4f52-84b2-438552e227be"


def test_node_that_no_longer_exists_is_left_out(api: responses.RequestsMock) -> None:
    _serve_recorded_nodes(api, statuses={HOST_1: HTTPStatus.NOT_FOUND})
    api.assert_all_requests_are_fired = False

    assert [section.target for section in fetch_nodes(_context(hosts=_recorded_host_list()))] == [
        "host-3",
        "host-2",
    ]


def test_not_found_for_every_node_fails_the_fetcher(api: responses.RequestsMock) -> None:
    host_stats = _recorded("clustermgmt_stats_hosts.json")
    _serve_recorded_nodes(api, statuses=dict.fromkeys(host_stats, HTTPStatus.NOT_FOUND))
    api.assert_all_requests_are_fired = False

    with pytest.raises(PrismV4Error, match="every host"):
        fetch_nodes(_context(hosts=_recorded_host_list()))


def test_nodes_without_a_cluster_give_no_sections(api: responses.RequestsMock) -> None:
    hosts = [
        {key: value for key, value in host.items() if key != "cluster"}
        for host in _recorded_host_list()
    ]
    _serve_recorded_nodes(api)
    api.assert_all_requests_are_fired = False

    assert fetch_nodes(_context(hosts=hosts)) == []


def test_nodes_fail_if_the_host_list_failed() -> None:
    error = PrismV4Error("clustermgmt/v4.0/config/hosts: timed out")

    with pytest.raises(PrismV4Error, match="timed out"):
        fetch_nodes(_context(hosts=error))


def _disk_calls(api: responses.RequestsMock) -> int:
    return sum(
        f"/api/{DISKS_PATH}" in (call.request.url or "")
        or f"/api/{DISK_STATS_PATH}/" in (call.request.url or "")
        for call in api.calls
    )


def test_disks_are_fetched_once_per_run(api: responses.RequestsMock) -> None:
    _serve_recorded_nodes(api)
    context = _context(hosts=_recorded_host_list())

    first = fetch_nodes(context)

    # The disk list and the stats of each of its 18 disks
    assert (_disk_calls(api), fetch_nodes(context), _disk_calls(api)) == (19, first, 19)


def test_failed_disk_list_is_not_fetched_again(api: responses.RequestsMock) -> None:
    api.get(v4_url(DISKS_PATH), status=HTTPStatus.FORBIDDEN, json={"message": "Forbidden"})
    context = _context()

    errors = []
    for _run in range(2):
        with pytest.raises(PrismV4Error) as error:
            fetch_nodes(context)
        errors.append(error.value)

    assert (_disk_calls(api), errors[0] is errors[1]) == (1, True)


def test_disk_that_no_longer_exists_is_kept_without_stats(api: responses.RequestsMock) -> None:
    _serve_recorded_nodes(
        api, statuses={"1ff5a5d9-e42a-4413-9f4e-f70b38fe4c44": HTTPStatus.NOT_FOUND}
    )

    assert isinstance(
        host_2 := _payload_of("host-2", fetch_nodes(_context(hosts=_recorded_host_list()))), dict
    )
    assert [disk["stats"] for disk in host_2["disks"] if disk["config"]["location"] == 4097] == [
        {"diskCapacityBytes": [], "diskFreeBytes": []}
    ]


def test_host_stats_error_other_than_not_found_fails_the_fetcher(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_nodes(
        api, statuses={"387a54c1-7286-49aa-9602-a7e8e889f63c": HTTPStatus.FORBIDDEN}
    )
    api.assert_all_requests_are_fired = False

    with pytest.raises(PrismV4Error):
        fetch_nodes(_context(hosts=_recorded_host_list()))


def test_disk_stats_error_loses_only_the_disk_stats_with_a_warning(
    api: responses.RequestsMock,
) -> None:
    disk_stats = _recorded("clustermgmt_stats_disks.json")
    _serve_recorded_nodes(api, statuses=dict.fromkeys(disk_stats, HTTPStatus.FORBIDDEN))
    api.assert_all_requests_are_fired = False
    messages = AgentMessages()

    sections = fetch_nodes(_context(messages, _recorded_host_list()))

    assert {section.target: _disk_stats_of(section) for section in sections} == dict.fromkeys(
        ("host-3", "host-1", "host-2"), [{"diskCapacityBytes": [], "diskFreeBytes": []}] * 6
    )
    assert [state for state, _text in messages] == ["warning"]


def test_node_without_a_name_is_not_routed(api: responses.RequestsMock) -> None:
    hosts = [
        {key: value for key, value in host.items() if key != "hostName"}
        for host in _recorded_host_list()
    ]
    _serve_recorded_nodes(api)

    assert {section.target for section in fetch_nodes(_context(hosts=hosts))} == {
        Unroutable("hosts without a name")
    }


def _serve_recorded_host_nics(
    api: responses.RequestsMock, nics: Sequence[object] | None = None
) -> None:
    """The 24 NICs of the lab's three hosts (anonymised), unless given"""
    api.get(
        v4_url(HOST_NICS_PATH),
        json=_recorded("clustermgmt_config_host_nics.json")
        if nics is None
        else page(nics, has_next=False),
        match=[
            page_matcher(0),
            matchers.query_param_matcher(
                {"$select": "name,macAddress,linkSpeedInKbps,interfaceStatus,nodeUuid"},
                strict_match=False,
            ),
        ],
    )


def _nic_names(sections: Sequence[Section]) -> dict[object, list[object]]:
    names: dict[object, list[object]] = {}
    for section in sections:
        assert isinstance(section.payload, list)
        names[section.target] = sorted(nic["name"] for nic in section.payload)
    return names


def test_each_host_gets_its_nics_with_only_the_checked_fields(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_host_nics(api)

    sections = fetch_host_nics(_context(hosts=_recorded_host_list()))

    assert {section.name for section in sections} == {"prism_host_networks_v2"}
    assert _nic_names(sections) == dict.fromkeys(
        ("host-1", "host-2", "host-3"), [f"eth{number}" for number in range(8)]
    )
    assert _payload_of("host-2", sections) == _recorded("section_prism_host_networks_v2.json")


def test_host_without_nics_gets_an_empty_section(api: responses.RequestsMock) -> None:
    _serve_recorded_host_nics(api, nics=[])

    assert _nic_names(fetch_host_nics(_context(hosts=_recorded_host_list()))) == dict.fromkeys(
        ("host-1", "host-2", "host-3"), []
    )


def test_nic_of_an_unknown_host_is_not_routed(api: responses.RequestsMock) -> None:
    _serve_recorded_host_nics(
        api,
        nics=[
            {"extId": "nic-1", "name": "eth0", "nodeUuid": "unknown-host"},
            {"extId": "nic-2", "name": "eth1"},
        ],
    )

    assert _nic_names(fetch_host_nics(_context(hosts=_recorded_host_list())))[
        Unroutable("host NICs without a known host")
    ] == ["eth0", "eth1"]


def test_host_nics_fail_if_the_host_list_failed() -> None:
    error = PrismV4Error("clustermgmt/v4.0/config/hosts: timed out")

    with pytest.raises(PrismV4Error, match="timed out"):
        fetch_host_nics(_context(hosts=error))


def test_nic_that_does_not_fit_the_model_is_skipped_with_an_info(
    api: responses.RequestsMock,
) -> None:
    _serve_recorded_host_nics(
        api,
        nics=[
            {"extId": "nic-1", "name": "eth0", "nodeUuid": HOST_1, "linkSpeedInKbps": "fast"},
            {"extId": "nic-2", "name": "eth1", "nodeUuid": HOST_1},
        ],
    )
    messages = AgentMessages()

    sections = fetch_host_nics(_context(messages, _recorded_host_list()))

    assert _nic_names(sections)["host-1"] == ["eth1"]
    assert list(messages) == [
        (
            "info",
            "Skipped host NIC 'eth0': Prism Central reports no valid linkSpeedInKbps for it",
        )
    ]


def test_host_without_a_cluster_gets_no_nics_section(api: responses.RequestsMock) -> None:
    hosts = [
        {key: value for key, value in host.items() if key != "cluster"}
        if host["extId"] == HOST_1
        else host
        for host in _recorded_host_list()
    ]
    _serve_recorded_host_nics(api)

    assert set(_nic_names(fetch_host_nics(_context(hosts=hosts)))) == {
        "host-2",
        "host-3",
        Unroutable("host NICs without a known host"),
    }


def test_hosts_sharing_a_name_get_a_nics_section_each(api: responses.RequestsMock) -> None:
    hosts = [{**host, "hostName": "host"} for host in _recorded_host_list()]
    _serve_recorded_host_nics(api)

    assert [
        (section.target, len(section.payload))
        for section in fetch_host_nics(_context(hosts=hosts))
        if isinstance(section.payload, list)
    ] == [("host", 8)] * 3


def test_storage_pool_goes_to_the_host_of_its_cluster_with_its_disks(
    api: responses.RequestsMock,
) -> None:
    """Each series keeps all samples of the window, the parse function picks the newest"""
    _serve_recorded_disks(api)

    assert fetch_storage_pools(_context()) == [
        Section(
            "prism_storage_pools_v2",
            _recorded("section_prism_storage_pools_v2.json"),
            CLUSTER_HOST,
        )
    ]


def test_storage_pools_and_nodes_share_the_disks(api: responses.RequestsMock) -> None:
    _serve_recorded_nodes(api)
    context = _context(hosts=_recorded_host_list())

    fetch_storage_pools(context)
    fetch_nodes(context)

    assert _disk_calls(api) == 19


def test_disk_stats_error_fails_the_storage_pools_and_warns_on_the_nodes(
    api: responses.RequestsMock,
) -> None:
    disk_stats = _recorded("clustermgmt_stats_disks.json")
    _serve_recorded_nodes(api, statuses=dict.fromkeys(disk_stats, HTTPStatus.FORBIDDEN))
    api.assert_all_requests_are_fired = False
    messages = AgentMessages()
    context = _context(messages, _recorded_host_list())

    with pytest.raises(PrismV4Error, match="403"):
        fetch_storage_pools(context)
    fetch_nodes(context)

    assert [state for state, _text in messages] == ["warning"]


def test_disk_without_a_pool_is_left_out(api: responses.RequestsMock) -> None:
    disks = _recorded("clustermgmt_config_disks.json")
    assert isinstance(listed := disks["data"], list)
    api.get(
        v4_url(DISKS_PATH),
        json={**disks, "data": [{**listed[0], "storagePoolExtId": None}, *listed[1:]]},
        match=[page_matcher(0)],
    )
    for disk_id, response in _recorded("clustermgmt_stats_disks.json").items():
        _serve_stats(api, f"{DISK_STATS_PATH}/{disk_id}", response, HTTPStatus.OK, {})

    sections = fetch_storage_pools(_context())

    assert isinstance(pools := sections[0].payload, list)
    assert [len(pool["disks"]) for pool in pools] == [17]


def _cluster_context(messages: AgentMessages | None = None) -> FetchContext:
    return FetchContext(
        _context().client,
        _recorded_cluster_list(),
        _routing(),
        AgentMessages() if messages is None else messages,
    )


def test_cluster_info_goes_to_its_cluster_or_prism_central_with_only_the_checked_fields(
    api: responses.RequestsMock,
) -> None:
    """Each stats series keeps all samples of the window, the parse function picks the newest"""
    _serve_cluster_stats(api)

    sections = fetch_clusters(_cluster_context())

    assert sections == [
        Section("prism_info_v2", _cluster_section("cluster-a"), CLUSTER_HOST),
        Section("prism_info_v2", _cluster_section("prism-central"), None),
    ]


def test_cluster_stats_are_the_last_samples_of_five_minutes_every_30_seconds(
    api: responses.RequestsMock,
) -> None:
    _serve_cluster_stats(api)

    fetch_clusters(_cluster_context())

    query = _sent_query(api)
    assert (
        query["$samplingInterval"],
        query["$statType"],
        datetime.fromisoformat(query["$endTime"]) - datetime.fromisoformat(query["$startTime"]),
    ) == ("30", "LAST", timedelta(minutes=5))


def test_cluster_stats_select_no_fields(api: responses.RequestsMock) -> None:
    """Prism Central fails the whole call for a selected field it doesn't know"""
    _serve_cluster_stats(api)

    fetch_clusters(_cluster_context())

    assert "$select" not in _sent_query(api)


def test_prism_central_stats_are_not_requested(
    api: responses.RequestsMock,
) -> None:
    """Prism Central refuses the stats of its own entry"""
    _serve_cluster_stats(api)

    fetch_clusters(_cluster_context())

    assert [call.request.path_url.split("?")[0] for call in api.calls] == [
        f"/api/{CLUSTER_STATS_PATH}/{CLUSTER_ID}"
    ]


def test_cluster_without_stats_is_reported_without_them_with_an_info(
    api: responses.RequestsMock,
) -> None:
    _serve_cluster_stats(api, status=HTTPStatus.NOT_FOUND)
    messages = AgentMessages()

    sections = fetch_clusters(_cluster_context(messages))

    assert (sections[0].payload, list(messages)) == (
        _cluster_section_without_stats("cluster-a"),
        [
            (
                "info",
                (
                    "Could not fetch the stats of 1 of 1 clusters: "
                    f"{CLUSTER_STATS_PATH}/{CLUSTER_ID}: HTTP 404 Not Found"
                ),
            )
        ],
    )


def test_failing_cluster_stats_cost_only_that_cluster_its_stats_with_a_warning(
    api: responses.RequestsMock,
) -> None:
    _serve_cluster_stats(api, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    messages = AgentMessages()

    sections = fetch_clusters(_cluster_context(messages))

    assert (sections, list(messages)) == (
        [
            Section("prism_info_v2", _cluster_section_without_stats("cluster-a"), CLUSTER_HOST),
            Section("prism_info_v2", _cluster_section("prism-central"), None),
        ],
        [
            (
                "warning",
                (
                    "Could not fetch the stats of 1 of 1 clusters: "
                    f"{CLUSTER_STATS_PATH}/{CLUSTER_ID}: HTTP 500 Internal Server Error"
                ),
            )
        ],
    )


def test_failing_stats_of_several_clusters_are_reported_once(
    api: responses.RequestsMock,
) -> None:
    recorded = {cluster["extId"]: cluster for cluster in _recorded_cluster_list()}
    failing = {
        "000645cc-2b3a-3b1c-06a8-7cc255ec36bb": HTTPStatus.INTERNAL_SERVER_ERROR,
        "000645cc-2b3a-3b1c-06a8-7cc255ec36cc": HTTPStatus.FORBIDDEN,
    }
    clusters = [
        recorded[PRISM_CENTRAL_ID],
        recorded[CLUSTER_ID],
        *(
            {**recorded[CLUSTER_ID], "extId": ext_id, "name": f"cluster-{ext_id[-2:]}"}
            for ext_id in failing
        ),
    ]
    _serve_cluster_stats(api)
    for ext_id, status in failing.items():
        api.get(
            v4_url(f"{CLUSTER_STATS_PATH}/{ext_id}"), status=status, json={"message": status.phrase}
        )
    messages = AgentMessages()

    fetch_clusters(
        FetchContext(_context().client, clusters, ClusterRouting.from_clusters(clusters), messages)
    )

    assert list(messages) == [
        (
            "warning",
            (
                "Could not fetch the stats of 2 of 3 clusters: "
                f"{CLUSTER_STATS_PATH}/000645cc-2b3a-3b1c-06a8-7cc255ec36bb: "
                "HTTP 500 Internal Server Error"
            ),
        )
    ]


def test_cluster_that_does_not_fit_the_model_is_skipped_with_an_info() -> None:
    messages = AgentMessages()
    context = FetchContext(_context().client, [{"name": "broken"}], _routing(), messages)

    sections = fetch_clusters(context)

    assert (sections, list(messages)) == (
        [],
        [("info", "Skipped cluster 'broken': Prism Central reports no valid extId for it")],
    )
