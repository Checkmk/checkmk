#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import time
from collections.abc import Callable, Iterable, Mapping
from typing import Literal

import pytest
from pytest import MonkeyPatch

from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import SectionName

from cmk.snmplib import SNMPBackendEnum

from cmk.checkengine.checking import AggregatedResult, CheckPluginName, ConfiguredService
from cmk.checkengine.checkresults import ServiceCheckResult, SubmittableServiceCheckResult
from cmk.checkengine.fetcher import HostKey, SourceType
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.parser import AgentRawDataSection, HostSections
from cmk.checkengine.sectionparser import (
    ParsedSectionName,
    ParsedSectionsResolver,
    Provider,
    SectionPlugin,
    SectionsParser,
)

from cmk.base import checkers, config
from cmk.base.api.agent_based.plugin_classes import CheckPlugin

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    PredictionInfo,
    PredictionParameters,
)
from cmk.agent_based.v1 import Metric, Result, State
from cmk.agent_based.v2 import CheckResult
from cmk.discover_plugins import PluginLocation


def make_timespecific_params_list(
    entries: Iterable[Mapping[str, object]],
) -> TimespecificParameters:
    return TimespecificParameters([TimespecificParameterSet.from_parameters(e) for e in entries])


@pytest.mark.parametrize(
    "subresults, aggregated_results",
    [
        ([], SubmittableServiceCheckResult.item_not_found()),
        (
            [
                Result(state=State.OK, notice="details"),
            ],
            SubmittableServiceCheckResult(
                0, "Everything looks OK - 1 detail available\ndetails", []
            ),
        ),
        (
            [
                Result(state=State.OK, summary="summary1", details="detailed info1"),
                Result(state=State.WARN, summary="summary2", details="detailed info2"),
            ],
            SubmittableServiceCheckResult(
                1, "summary1, summary2(!)\ndetailed info1\ndetailed info2(!)", []
            ),
        ),
        (
            [
                Result(state=State.OK, summary="summary"),
                Metric(name="name", value=42),
            ],
            SubmittableServiceCheckResult(
                0, "summary\nsummary", [("name", 42.0, None, None, None, None)]
            ),
        ),
    ],
)
def test_aggregate_result(subresults: CheckResult, aggregated_results: ServiceCheckResult) -> None:
    assert (
        checkers._aggregate_results(checkers.consume_check_results(subresults))
        == aggregated_results
    )


def test_consume_result_invalid() -> None:
    def offending_check_function() -> Iterable[object]:
        yield None

    with pytest.raises(TypeError):
        assert checkers.consume_check_results(offending_check_function())


def test_config_cache_get_clustered_service_node_keys_no_cluster(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda *args, **kw: "dummy.test.ip.0",
    )
    # empty, we have no cluster:
    assert [] == checkers._get_clustered_service_node_keys(
        HostName("cluster.test"),
        SourceType.HOST,
        "Test Service",
        cluster_nodes=(),
        get_effective_host=lambda hn, *args, **kw: hn,
    )


def test_config_cache_get_clustered_service_node_keys_cluster_no_service(
    monkeypatch: MonkeyPatch,
) -> None:
    cluster_test = HostName("cluster.test")
    ts = Scenario()
    ts.add_cluster(cluster_test, nodes=[HostName("node1.test"), HostName("node2.test")])

    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda *args, **kw: "dummy.test.ip.0",
    )
    # empty for a node:
    assert [] == checkers._get_clustered_service_node_keys(
        HostName("node1.test"),
        SourceType.HOST,
        "Test Service",
        cluster_nodes=(),
        get_effective_host=lambda hn, *args, **kw: hn,
    )

    # empty for cluster (we have not clustered the service)
    assert [
        HostKey(hostname=HostName("node1.test"), source_type=SourceType.HOST),
        HostKey(hostname=HostName("node2.test"), source_type=SourceType.HOST),
    ] == checkers._get_clustered_service_node_keys(
        cluster_test,
        SourceType.HOST,
        "Test Service",
        cluster_nodes=[HostName("node1.test"), HostName("node2.test")],
        get_effective_host=lambda hn, *args, **kw: hn,
    )


def test_config_cache_get_clustered_service_node_keys_clustered(monkeypatch: MonkeyPatch) -> None:
    node1 = HostName("node1.test")
    node2 = HostName("node2.test")
    cluster = HostName("cluster.test")

    ts = Scenario()
    ts.add_host(node1)
    ts.add_host(node2)
    ts.add_cluster(cluster, nodes=[node1, node2])
    # add a fake rule, that defines a cluster
    ts.set_option(
        "clustered_services_mapping",
        [
            {
                "value": "cluster.test",
                "condition": {"service_description": ["Test Service"]},
            }
        ],
    )

    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda hostname, *args, **kw: "dummy.test.ip.%s" % hostname[4],
    )
    assert checkers._get_clustered_service_node_keys(
        cluster,
        SourceType.HOST,
        "Test Service",
        cluster_nodes=[node1, node2],
        get_effective_host=lambda hn, *args, **kw: hn,
    ) == [
        HostKey(node1, SourceType.HOST),
        HostKey(node2, SourceType.HOST),
    ]
    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda *args, **kw: "dummy.test.ip.0",
    )
    assert [
        HostKey(hostname=HostName("node1.test"), source_type=SourceType.HOST),
        HostKey(hostname=HostName("node2.test"), source_type=SourceType.HOST),
    ] == checkers._get_clustered_service_node_keys(
        cluster,
        SourceType.HOST,
        "Test Unclustered",
        cluster_nodes=[node1, node2],
        get_effective_host=lambda hn, *args, **kw: hn,
    )


def test_only_from_injection() -> None:
    p_config = checkers.PostprocessingConfig(
        only_from=lambda: ["1.2.3.4"],
        prediction=lambda: InjectedParameters(meta_file_path_template="", predictions={}),
        service_level=lambda: 42,
        host_name="not-relevant-for-test",
        service_name="not-relevant-for-test",
    )
    p: dict[str, object] = {
        "outer": {
            "inner": ("cmk_postprocessed", "only_from", None),
        },
    }
    assert checkers.postprocess_configuration(p, p_config) == {
        "outer": {
            "inner": ["1.2.3.4"],
        },
    }


def test_prediction_injection_legacy() -> None:
    p_config = checkers.PostprocessingConfig(
        only_from=lambda: ["1.2.3.4"],
        prediction=lambda: InjectedParameters(meta_file_path_template="", predictions={}),
        service_level=lambda: 42,
        host_name="not-relevant-for-test",
        service_name="not-relevant-for-test",
    )
    p: dict[str, object] = {
        "pagefile": (
            "predictive",
            {
                "__injected__": None,
                "period": "day",
                "horizon": 60,
                "levels_upper": ("absolute", (0.5, 1.0)),
            },
        )
    }
    assert checkers.postprocess_configuration(p, p_config) == {
        "pagefile": (
            "predictive",
            {
                "__injected__": p_config.prediction().model_dump(),
                "period": "day",
                "horizon": 60,
                "levels_upper": ("absolute", (0.5, 1.0)),
            },
        )
    }


def _make_hash(params: PredictionParameters, direction: Literal["upper"], metric: str) -> int:
    # particular values of prediction parameters are irrelevant for this test.
    return hash(PredictionInfo.make(metric, direction, params, time.time()))


def test_prediction_injection() -> None:
    # particular values of prediction parameters are irrelevant for this test.
    params = PredictionParameters(period="day", horizon=90, levels=("stdev", (2.0, 4.0)))
    metric = "my_reference_metric"
    prediction = (42.0, (50.0, 60.0))

    p_config = checkers.PostprocessingConfig(
        only_from=lambda: [],
        prediction=lambda: InjectedParameters(
            meta_file_path_template="",
            predictions={_make_hash(params, "upper", metric): prediction},
        ),
        service_level=lambda: 42,
        host_name="not-relevant-for-test",
        service_name="not-relevant-for-test",
    )
    p: dict[str, object] = {
        "levels_upper": (
            "cmk_postprocessed",
            "predictive_levels",
            {
                "__reference_metric__": "my_reference_metric",
                "__direction__": "upper",
                "period": params.period,
                "horizon": params.horizon,
                "levels": params.levels,
            },
        ),
    }
    assert checkers.postprocess_configuration(p, p_config) == {
        "levels_upper": (
            "predictive",
            ("my_reference_metric", *prediction),
        )
    }


def _make_check_plugin() -> CheckPlugin:
    return CheckPlugin(
        name=CheckPluginName("plugin"),
        sections=[ParsedSectionName("section")],
        service_name="Service",
        discovery_function=lambda *args, **kw: iter(()),
        discovery_default_parameters=None,
        discovery_ruleset_name=None,
        discovery_ruleset_type="merged",
        check_function=lambda *args, **kw: iter(()),
        check_default_parameters={},
        check_ruleset_name=None,
        cluster_check_function=None,
        location=PluginLocation("not", "relevant"),
    )


def _make_providers(host_name: HostName) -> Mapping[HostKey, Provider]:
    return {
        HostKey(host_name, SourceType.HOST): ParsedSectionsResolver(
            SectionsParser(
                HostSections[AgentRawDataSection](sections={SectionName("section"): [["data"]]}),
                host_name=host_name,
                error_handling=lambda *args, **kw: "error",
            ),
            section_plugins={SectionName("section"): SectionPlugin.trivial(SectionName("section"))},
        )
    }


def _get_aggregated_result(
    host_name: HostName,
    service: ConfiguredService,
    check_function: Callable[..., ServiceCheckResult],
) -> AggregatedResult:
    return checkers.get_aggregated_result(
        host_name,
        False,
        cluster_nodes=(),
        providers=_make_providers(host_name),
        service=service,
        plugin=_make_check_plugin(),
        check_function=check_function,
        get_parameters=lambda: service.parameters.evaluate(lambda _timeperiod: True),
        rtc_package=None,
        get_effective_host=lambda host_name, _service_name: host_name,
        snmp_backend=SNMPBackendEnum.CLASSIC,
    )


def _make_service(raw_parameters: object) -> ConfiguredService:
    return ConfiguredService(
        check_plugin_name=CheckPluginName("plugin"),
        item="item",
        description="Service item",
        parameters=TimespecificParameters(
            # Invalid on purpose: rule values are not validated when loaded.
            [TimespecificParameterSet.from_parameters(raw_parameters)]  # type: ignore[arg-type]
        ),
        discovered_parameters={},
        discovered_labels={},
        is_enforced=True,
    )


def test_get_aggregated_result_passes_parameters() -> None:
    host_name = HostName("host")
    received: dict[str, object] = {}

    def check_function(**kwargs: object) -> ServiceCheckResult:
        received.update(kwargs)
        return SubmittableServiceCheckResult(0, "OK")

    result = _get_aggregated_result(host_name, _make_service({"levels": (1, 2)}), check_function)

    assert result.result == SubmittableServiceCheckResult(0, "OK")
    assert received["params"] == {"levels": (1, 2)}


@pytest.mark.usefixtures("disable_debug")
@pytest.mark.parametrize(
    "raw_parameters",
    [
        pytest.param(
            ("process.exe", 1500, 2000, 1000, 1500, 80.0, 90.0),
            id="legacy tuple",
        ),
        pytest.param(["process.exe", 1, 1, 1, 1], id="list"),
        pytest.param("process.exe", id="string"),
        pytest.param(
            {"tp_default_value": {}, "tp_values": [("always", ("process.exe", 1))]},
            id="time specific value is not a mapping",
        ),
    ],
)
def test_get_aggregated_result_invalid_parameters_only_affect_service(
    monkeypatch: MonkeyPatch, raw_parameters: object
) -> None:
    host_name = HostName("host")
    monkeypatch.setattr(checkers, "create_check_crash_dump", lambda *args, **kw: "crash dump")

    calls: list[Mapping[str, object]] = []

    def check_function(**kwargs: object) -> ServiceCheckResult:
        calls.append(kwargs)
        return SubmittableServiceCheckResult(0, "OK")

    result = _get_aggregated_result(host_name, _make_service(raw_parameters), check_function)

    assert not calls
    assert result.data_received
    assert result.result == SubmittableServiceCheckResult(3, "crash dump")
