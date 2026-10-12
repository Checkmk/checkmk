#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import socket
import time
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Literal

import pytest
from pytest import MonkeyPatch

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    PredictionInfo,
    PredictionParameters,
)
from cmk.agent_based.v1 import Metric, Result, State
from cmk.agent_based.v2 import CheckResult
from cmk.base import checkers
from cmk.base.checkers import CMKFetcher
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.ccc import resulttype as result
from cmk.ccc.exceptions import MKTimeout, OnError
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.checkerplugin import AggregatedResult, ConfiguredService
from cmk.checkengine.checkresults import ServiceCheckResult, SubmittableServiceCheckResult
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.fetcher import HostKey
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.parser import AgentRawDataSection, HostSections
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckPlugin,
    CheckPluginName,
    ParsedSectionName,
    SectionName,
)
from cmk.checkengine.sectionparser import (
    ParsedSectionsResolver,
    Provider,
    SectionPlugin,
    SectionsParser,
)
from cmk.checkengine.summarize import SummaryConfig
from cmk.discover_plugins import PluginLocation
from cmk.fetchers import (
    AdHocSecrets,
    Mode,
    NoSelectedSNMPSections,
    PlainFetcherTrigger,
    SNMPFetcherConfig,
    StoredSecrets,
)
from cmk.fetchers.filecache import FileCacheOptions
from cmk.helper_interface import FetcherType, SourceInfo, SourceType
from cmk.piggyback.backend import Config as PiggybackConfig
from cmk.snmplib import SNMPBackendEnum
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.servicename import ServiceName
from tests.testlib.unit.base_configuration_scenario import Scenario


def make_timespecific_params_list(
    entries: Iterable[Mapping[str, object]],
) -> TimespecificParameters:
    return TimespecificParameters([TimespecificParameterSet.from_parameters(e) for e in entries])


def make_service(description: ServiceName) -> ConfiguredService:
    return ConfiguredService(
        CheckPluginName("dummy"), None, description, TimespecificParameters(), {}, {}, {}, False
    )


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


def test_config_cache_get_clustered_service_node_keys_no_cluster() -> None:
    # empty, we have no cluster:
    assert [] == checkers._get_clustered_service_node_keys(
        HostName("cluster.test"),
        SourceType.HOST,
        make_service("Test Service"),
        cluster_nodes=(),
        get_effective_host=lambda hn, *args, **kw: hn,
    )


def test_config_cache_get_clustered_service_node_keys_cluster_no_service() -> None:
    cluster_test = HostName("cluster.test")

    # empty for a node:
    assert [] == checkers._get_clustered_service_node_keys(
        HostName("node1.test"),
        SourceType.HOST,
        make_service("Test Service"),
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
        make_service("Test Service"),
        cluster_nodes=[HostName("node1.test"), HostName("node2.test")],
        get_effective_host=lambda hn, *args, **kw: hn,
    )


def test_config_cache_get_clustered_service_node_keys_clustered() -> None:
    node1 = HostName("node1.test")
    node2 = HostName("node2.test")
    cluster = HostName("cluster.test")

    assert checkers._get_clustered_service_node_keys(
        cluster,
        SourceType.HOST,
        make_service("Test Service"),
        cluster_nodes=[node1, node2],
        get_effective_host=lambda hn, *args, **kw: hn,
    ) == [
        HostKey(node1, SourceType.HOST),
        HostKey(node2, SourceType.HOST),
    ]
    assert [
        HostKey(hostname=HostName("node1.test"), source_type=SourceType.HOST),
        HostKey(hostname=HostName("node2.test"), source_type=SourceType.HOST),
    ] == checkers._get_clustered_service_node_keys(
        cluster,
        SourceType.HOST,
        make_service("Test Unclustered"),
        cluster_nodes=[node1, node2],
        get_effective_host=lambda hn, *args, **kw: hn,
    )


def test_only_from_injection() -> None:
    p_config = checkers.PostprocessingServiceConfig(
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
    p_config = checkers.PostprocessingServiceConfig(
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


def test_cmk_summarizer_no_data_sources() -> None:
    summarizer = checkers.CMKSummarizer(
        HostName("test-host"),
        lambda _hn, _ident: None,  # type: ignore[return-value,arg-type]
    )
    (res,) = summarizer([])
    assert res.state == 3


def _summary_config(_hn: HostName, _ident: str) -> SummaryConfig:
    return SummaryConfig(
        exit_spec=ExitSpec(),
        piggyback_config=PiggybackConfig(HostName("hostname"), []),
        expect_data=False,
    )


def _agent_source(hostname: HostName) -> SourceInfo:
    return SourceInfo(
        hostname=hostname,
        ipaddress=None,
        ident="agent",
        fetcher_type=FetcherType.TCP,
        source_type=SourceType.HOST,
    )


def test_cmk_summarizer_annotates_cluster_node_on_failure() -> None:
    summarizer = checkers.CMKSummarizer(HostName("my-cluster"), _summary_config)
    (res,) = summarizer(
        [(_agent_source(HostName("node02")), result.Error(MKTimeout("Agent timeout")))]
    )
    assert res.state == 2
    # The "(!!)" marker is the CRIT state marker appended by ActiveCheckResult.
    assert res.summary == "[agent] Agent timeout on node node02(!!)"


def test_cmk_summarizer_no_node_suffix_for_regular_host() -> None:
    summarizer = checkers.CMKSummarizer(HostName("my-host"), _summary_config)
    (res,) = summarizer(
        [
            (
                _agent_source(HostName("my-host")),
                result.OK(HostSections({})),
            )
        ]
    )
    assert res.state == 0
    assert res.summary == "[agent] Success"


def _make_hash(params: PredictionParameters, direction: Literal["upper"], metric: str) -> int:
    # particular values of prediction parameters are irrelevant for this test.
    return hash(PredictionInfo.make(metric, direction, params, time.time()))


def test_prediction_injection() -> None:
    # particular values of prediction parameters are irrelevant for this test.
    params = PredictionParameters(period="day", horizon=90, levels=("stdev", (2.0, 4.0)))
    metric = "my_reference_metric"
    prediction = (42.0, (50.0, 60.0))

    p_config = checkers.PostprocessingServiceConfig(
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


@pytest.mark.usefixtures("patch_omd_site")
def test_cmk_fetcher_reports_missing_ip_instead_of_the_fallback_address(
    monkeypatch: MonkeyPatch,
) -> None:
    """A failed address lookup must not be papered over with a fallback address.

    A tolerant IP lookup answers with ``0.0.0.0`` when it could not resolve the
    host.  Handing that on to the fetchers points them at the local system, so
    the fetcher turns it into "no address": the sources that need one report
    `MISSING_IP`, the sources that do not are unaffected.  See SUP-30417.
    """
    testhost = HostName("nodns-host")
    ts = Scenario()
    ts.add_host(testhost)  # no explicit address, name does not resolve
    config_cache = ts.apply(monkeypatch)
    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(config_cache._loaded_config, config_cache.ruleset_matcher)
    )
    plugins = AgentBasedPlugins(
        agent_sections={}, snmp_sections={}, check_plugins={}, inventory_plugins={}, errors=()
    )

    fetcher = CMKFetcher(
        config_cache,
        get_relay_id=lambda hn: None,
        make_trigger=lambda relay_id: PlainFetcherTrigger(Path("/")),
        factory=config_cache.fetcher_factory(
            config_cache.make_service_configurer({}, service_name_config),
            lambda *a: HostAddress(""),
            service_name_config,
            lambda hn: {},
            SNMPFetcherConfig(
                on_error=OnError.RAISE,
                missing_sys_description=lambda host_name: False,
                selected_sections=NoSelectedSNMPSections(),
                backend_override=None,
                base_path=Path("/"),
                relative_stored_walk_path=Path("dev/null"),
                relative_walk_cache_path=Path("dev/null"),
                relative_section_cache_path=Path("dev/null"),
                caching_config=lambda host_name: {},
            ),
        ),
        plugins=plugins,
        default_address_family=lambda *a: socket.AddressFamily.AF_INET,
        file_cache_options=FileCacheOptions(),
        force_snmp_cache_refresh=False,
        get_ip_stack_config=lambda *a: IPStackConfig.IPv4,
        # what a tolerant lookup answers when DNS resolution failed
        ip_address_of=lambda *a: HostAddress("0.0.0.0"),
        ip_address_of_mgmt=lambda *a: None,
        mode=Mode.DISCOVERY,
        simulation_mode=False,
        secrets_config_relay=AdHocSecrets(path=Path("/pw/relay"), secrets={}),
        secrets_config_site=StoredSecrets(path=Path("/pw/store"), secrets={}),
        metric_backend_fetcher_factory=lambda hn: None,
    )

    fetched = fetcher(testhost, ip_address=None)

    agent_sources = [(source, res) for source, res, _snapshot in fetched if source.ident == "agent"]
    assert len(agent_sources) == 1
    source, res = agent_sources[0]
    assert source.ipaddress is None
    assert source.fetcher_type is FetcherType.NONE
    assert res.is_error()


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
        get_effective_host=lambda host_name, _service_name, _labels: host_name,
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
        labels={},
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
