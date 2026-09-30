#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import socket
import sys
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal, Protocol

import pytest
from pytest import MonkeyPatch

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    PredictionInfo,
    PredictionParameters,
)
from cmk.agent_based.v1 import Metric, Result, Service, State
from cmk.agent_based.v3_unstable import CheckResult as CheckResultV3Unstable
from cmk.agent_based.v3_unstable import DiscoveryResult, parse_as, ParseFailure
from cmk.agent_based.v3_unstable import Metric as MetricV3Unstable
from cmk.base import checkers
from cmk.base.checkers import CMKFetcher
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.ccc import resulttype as result
from cmk.ccc.exceptions import MKTimeout, OnError
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.checkerplugin import AggregatedResult, ConfiguredService
from cmk.checkengine.fetcher_abc import Mode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetcher_utils.trigger import PlainFetcherTrigger
from cmk.checkengine.fetchers.snmp import (
    NoSelectedSNMPSections,
    SNMPFetcherConfig,
)
from cmk.checkengine.filecache import FileCacheOptions
from cmk.checkengine.helper_interface import (
    AgentRawData,
    FetcherType,
    HostKey,
    SourceInfo,
    SourceType,
)
from cmk.checkengine.parser import AgentRawDataSection, HostSections
from cmk.checkengine.plugin_backend.check_plugins import create_check_plugin
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckPlugin,
    CheckPluginName,
    FinalCheckResult,
    ParsedSectionName,
    SectionName,
)
from cmk.checkengine.sectionparser import (
    make_providers,
    ParsedSectionsResolver,
    Provider,
    SectionPlugin,
    SectionsParser,
)
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.checkengine.specs.checkresults import (
    MetricTuple,
    ServiceCheckResult,
    SubmittableServiceCheckResult,
)
from cmk.checkengine.specs.exitspec import ExitSpec
from cmk.checkengine.specs.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.summarize import SummaryConfig
from cmk.checkengine.value_store import AllValueStoresStore, ValueStoreManager
from cmk.discover_plugins import PluginLocation
from cmk.piggyback.backend import Config as PiggybackConfig
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.servicename import ServiceName
from tests.testlib.unit.base_configuration_scenario import Scenario
from tests.testlib.unit.fake_site import pop_crash_report_file


def make_timespecific_params_list(
    entries: Iterable[Mapping[str, object]],
) -> TimespecificParameters:
    return TimespecificParameters([TimespecificParameterSet.from_parameters(e) for e in entries])


def make_service(description: ServiceName) -> ConfiguredService:
    return ConfiguredService(
        CheckPluginName("dummy"), None, description, TimespecificParameters(), {}, {}, {}, False
    )


def test_predictive_otel_metrics_hack_gate_covers_both_otel_plugins() -> None:
    assert (
        CheckPluginName("otel_metrics"),
        CheckPluginName("otel_azure_metrics"),
    ) == checkers._PLUGINS_WITH_PREDICTIVE_OTEL_METRICS_HACK  # noqa: SLF001


def test_special_processing_hack_for_predictive_otel_metrics_injects_reference_metric_and_direction() -> (
    None
):
    params: Mapping[str, object] = {
        "metrics": (
            "multi_metrics",
            [
                {
                    "metric_name": "azure_available_memory_bytes_average",
                    "levels_lower": ("cmk_postprocessed", "predictive_levels", {"period": "day"}),
                    "levels_upper": ("fixed", (50.0, 80.0)),
                }
            ],
        )
    }

    result = checkers._special_processing_hack_for_predictive_otel_metrics(params)  # noqa: SLF001

    assert result == {
        "metrics": (
            "multi_metrics",
            [
                {
                    "metric_name": "azure_available_memory_bytes_average",
                    "levels_lower": (
                        "cmk_postprocessed",
                        "predictive_levels",
                        {
                            "period": "day",
                            "__reference_metric__": "azure_available_memory_bytes_average",
                            "__direction__": "lower",
                        },
                    ),
                    "levels_upper": ("fixed", (50.0, 80.0)),
                }
            ],
        )
    }


def test_special_processing_hack_for_predictive_otel_metrics_defaults_missing_levels_lower() -> (
    None
):
    """Regression test for CMK-38135: the otel_azure_metrics ruleset allows configuring only
    upper levels for a metric, leaving "levels_lower" absent from the parameter dict entirely."""
    params: Mapping[str, object] = {
        "metrics": (
            "multi_metrics",
            [
                {
                    "metric_name": "azure_firewalllatencypng_average",
                    "levels_upper": (
                        "cmk_postprocessed",
                        "predictive_levels",
                        {"period": "minute"},
                    ),
                }
            ],
        )
    }

    result = checkers._special_processing_hack_for_predictive_otel_metrics(params)  # noqa: SLF001

    assert result == {
        "metrics": (
            "multi_metrics",
            [
                {
                    "metric_name": "azure_firewalllatencypng_average",
                    "levels_lower": ("no_levels", None),
                    "levels_upper": (
                        "cmk_postprocessed",
                        "predictive_levels",
                        {
                            "period": "minute",
                            "__reference_metric__": "azure_firewalllatencypng_average",
                            "__direction__": "upper",
                        },
                    ),
                }
            ],
        )
    }


def test_special_processing_hack_for_predictive_otel_metrics_defaults_missing_levels_upper() -> (
    None
):
    params: Mapping[str, object] = {
        "metrics": (
            "multi_metrics",
            [
                {
                    "metric_name": "azure_available_memory_bytes_average",
                    "levels_lower": ("fixed", (10.0, 5.0)),
                }
            ],
        )
    }

    result = checkers._special_processing_hack_for_predictive_otel_metrics(params)  # noqa: SLF001

    assert result == {
        "metrics": (
            "multi_metrics",
            [
                {
                    "metric_name": "azure_available_memory_bytes_average",
                    "levels_lower": ("fixed", (10.0, 5.0)),
                    "levels_upper": ("no_levels", None),
                }
            ],
        )
    }


def test_special_processing_hack_for_predictive_otel_metrics_multiple_metrics_missing_levels_lower() -> (
    None
):
    """Reproduces the exact crash payload from CMK-38135's crash report: two metrics, neither
    configuring a lower level, one with predictive upper levels and one with fixed upper levels."""
    params: Mapping[str, object] = {
        "metrics": (
            "multi_metrics",
            [
                {
                    "metric_name": "azure_firewalllatencypng_average",
                    "levels_upper": (
                        "cmk_postprocessed",
                        "predictive_levels",
                        {"period": "minute"},
                    ),
                },
                {
                    "metric_name": "azure_networkrulehit_total",
                    "levels_upper": ("fixed", (3.0, 5.0)),
                },
            ],
        )
    }

    result = checkers._special_processing_hack_for_predictive_otel_metrics(params)  # noqa: SLF001

    assert result == {
        "metrics": (
            "multi_metrics",
            [
                {
                    "metric_name": "azure_firewalllatencypng_average",
                    "levels_lower": ("no_levels", None),
                    "levels_upper": (
                        "cmk_postprocessed",
                        "predictive_levels",
                        {
                            "period": "minute",
                            "__reference_metric__": "azure_firewalllatencypng_average",
                            "__direction__": "upper",
                        },
                    ),
                },
                {
                    "metric_name": "azure_networkrulehit_total",
                    "levels_lower": ("no_levels", None),
                    "levels_upper": ("fixed", (3.0, 5.0)),
                },
            ],
        )
    }


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
                0,
                "summary\nsummary",
                [MetricTuple(name="name", value=42.0, warn=None, crit=None, min_=None, max_=None)],
            ),
        ),
    ],
)
def test_aggregate_result(
    subresults: FinalCheckResult, aggregated_results: ServiceCheckResult
) -> None:
    assert (
        checkers._aggregate_results(checkers._consume_check_results(subresults), [])  # noqa: SLF001
        == aggregated_results
    )


def test_config_cache_get_clustered_service_node_keys_no_cluster() -> None:
    # empty, we have no cluster:
    assert (
        checkers._get_clustered_service_node_keys(  # noqa: SLF001
            HostName("cluster.test"),
            SourceType.HOST,
            make_service("Test Service"),
            cluster_nodes=(),
            get_effective_host=lambda hn, *args, **kw: hn,  # noqa: ARG005
        )
        == []
    )


def test_config_cache_get_clustered_service_node_keys_cluster_no_service() -> None:
    cluster_test = HostName("cluster.test")

    # empty for a node:
    assert (
        checkers._get_clustered_service_node_keys(  # noqa: SLF001
            HostName("node1.test"),
            SourceType.HOST,
            make_service("Test Service"),
            cluster_nodes=(),
            get_effective_host=lambda hn, *args, **kw: hn,  # noqa: ARG005
        )
        == []
    )

    # empty for cluster (we have not clustered the service)
    assert [
        HostKey(hostname=HostName("node1.test"), source_type=SourceType.HOST),
        HostKey(hostname=HostName("node2.test"), source_type=SourceType.HOST),
    ] == checkers._get_clustered_service_node_keys(  # noqa: SLF001
        cluster_test,
        SourceType.HOST,
        make_service("Test Service"),
        cluster_nodes=[HostName("node1.test"), HostName("node2.test")],
        get_effective_host=lambda hn, *args, **kw: hn,  # noqa: ARG005
    )


def test_config_cache_get_clustered_service_node_keys_clustered() -> None:
    node1 = HostName("node1.test")
    node2 = HostName("node2.test")
    cluster = HostName("cluster.test")

    assert checkers._get_clustered_service_node_keys(  # noqa: SLF001
        cluster,
        SourceType.HOST,
        make_service("Test Service"),
        cluster_nodes=[node1, node2],
        get_effective_host=lambda hn, *args, **kw: hn,  # noqa: ARG005
    ) == [
        HostKey(node1, SourceType.HOST),
        HostKey(node2, SourceType.HOST),
    ]
    assert [
        HostKey(hostname=HostName("node1.test"), source_type=SourceType.HOST),
        HostKey(hostname=HostName("node2.test"), source_type=SourceType.HOST),
    ] == checkers._get_clustered_service_node_keys(  # noqa: SLF001
        cluster,
        SourceType.HOST,
        make_service("Test Unclustered"),
        cluster_nodes=[node1, node2],
        get_effective_host=lambda hn, *args, **kw: hn,  # noqa: ARG005
    )


def test_only_from_injection() -> None:
    p_config = checkers.PostprocessingServiceConfig(
        only_from=lambda: ["1.2.3.4"],
        prediction=lambda: InjectedParameters(meta_file_path_template="", predictions={}),
        service_level=lambda: 42,
        host_name="not-relevant-for-test",
        service_name="not-relevant-for-test",
        is_preview=False,
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
        is_preview=False,
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
        only_from=list,
        prediction=lambda: InjectedParameters(
            meta_file_path_template="",
            predictions={_make_hash(params, "upper", metric): prediction},
        ),
        service_level=lambda: 42,
        host_name="not-relevant-for-test",
        service_name="not-relevant-for-test",
        is_preview=False,
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


def test_is_preview_injection() -> None:
    p_config = checkers.PostprocessingServiceConfig(
        only_from=lambda: ["not-relevant-for-test"],
        prediction=lambda: InjectedParameters(meta_file_path_template="", predictions={}),
        service_level=lambda: 42,
        host_name="not-relevant-for-test",
        service_name="not-relevant-for-test",
        is_preview=True,
    )
    p: dict[str, object] = {
        "outer": {
            "inner": ("cmk_postprocessed", "is_preview", None),
        },
    }
    assert checkers.postprocess_configuration(p, p_config) == {
        "outer": {
            "inner": True,
        },
    }


def test_consume_check_results_clamps_inf_levels() -> None:
    perfdata = checkers._consume_check_results(  # noqa: SLF001
        [MetricV3Unstable("m", 1.0, levels=(float("inf"), float("-inf")))]
    ).metrics
    assert len(perfdata) == 1
    assert perfdata[0].warn == sys.float_info.max
    assert perfdata[0].crit == -sys.float_info.max


def test_consume_check_results_clamps_inf_lower_levels() -> None:
    perfdata = checkers._consume_check_results(  # noqa: SLF001
        [
            MetricV3Unstable(
                "m",
                1.0,
                lower_levels=(float("inf"), float("-inf")),
            )
        ]
    ).metrics
    assert len(perfdata) == 1
    assert perfdata[0].warn_lower == sys.float_info.max
    assert perfdata[0].crit_lower == -sys.float_info.max


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
    loading_result = ts.apply(monkeypatch)
    config_cache = loading_result.config_cache
    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(loading_result.loaded_config, config_cache.ruleset_matcher)
    )
    plugins = AgentBasedPlugins(
        agent_sections={}, snmp_sections={}, check_plugins={}, inventory_plugins={}, errors=()
    )

    fetcher = CMKFetcher(
        config_cache,
        loading_result.host_tags,
        get_relay_id=lambda hn: None,  # noqa: ARG005
        make_trigger=lambda hn: PlainFetcherTrigger(Path("/")),  # noqa: ARG005
        source_config=config_cache.make_source_config(
            config_cache.make_service_configurer({}, service_name_config),
            ip_lookup=lambda *a: HostAddress(""),  # noqa: ARG005
            service_name_config=service_name_config,
            enforced_services_table=lambda hn: {},  # noqa: ARG005
            snmp_fetcher_config=SNMPFetcherConfig(
                on_error=OnError.RAISE,
                missing_sys_description=lambda host_name: False,  # noqa: ARG005
                selected_sections=NoSelectedSNMPSections(),
                backend_override=None,
                base_path=Path("/"),
                relative_stored_walk_path=Path("dev/null"),
                relative_walk_cache_path=Path("dev/null"),
                relative_section_cache_path=Path("dev/null"),
                caching_config=lambda host_name: {},  # noqa: ARG005
                debug=True,
            ),
        ),
        plugins=plugins,
        clusters=loading_result.hosts_config.clusters,
        default_address_family=lambda *a: socket.AddressFamily.AF_INET,  # noqa: ARG005
        file_cache_options=FileCacheOptions(),
        force_snmp_cache_refresh=False,
        get_ip_stack_config=lambda *a: IPStackConfig.IPv4,  # noqa: ARG005
        # what a tolerant lookup answers when DNS resolution failed
        ip_address_of=lambda *a: HostAddress("0.0.0.0"),  # noqa: ARG005
        ip_address_of_mgmt=lambda *a: None,  # noqa: ARG005
        mode=Mode.DISCOVERY,
        simulation_mode=False,
        secrets_config_relay=AdHocSecrets(path=Path("/pw/relay"), secrets={}),
        secrets_config_site=StoredSecrets(path=Path("/pw/store"), secrets={}),
        debug=True,
    )

    fetched = fetcher(testhost, ip_address=None)

    agent_sources = [(f.source, f.raw_data) for f in fetched if f.source.ident == "agent"]
    assert len(agent_sources) == 1
    source, res = agent_sources[0]
    assert source.ipaddress is None
    assert source.fetcher_type is FetcherType.NONE
    assert res.is_error()


_OK_SUBRESULTS = checkers._Subresults((), (), [Result(state=State.OK, summary="OK")], ())  # noqa: SLF001


class _CheckFunction(Protocol):
    def __call__(self, **kwargs: object) -> checkers._Subresults: ...


def _aggregated_result_of(
    check_function: _CheckFunction,
    get_agent_output: Callable[[], AgentRawData | None],
) -> AggregatedResult:
    host_name = HostName("testhost")
    section_name = SectionName("uptime")
    provider = ParsedSectionsResolver(
        SectionsParser(
            HostSections[Mapping[SectionName, Sequence[Sequence[str]]]]({section_name: [["123"]]}),
            host_name,
            error_handling=lambda *_args: "",
            debug=True,
        ),
        section_plugins={section_name: SectionPlugin.trivial(section_name)},
    )
    return checkers.get_aggregated_result(
        host_name,
        False,
        cluster_nodes=(),
        providers={HostKey(host_name, SourceType.HOST): provider},
        service=make_service("Uptime"),
        plugin=CheckPlugin(
            name=CheckPluginName("dummy"),
            sections=[ParsedSectionName("uptime")],
            service_name="Uptime",
            discovery_function=lambda *args, **kw: iter(()),  # noqa: ARG005
            discovery_default_parameters=None,
            discovery_ruleset_name=None,
            discovery_ruleset_type="merged",
            check_function=lambda *args, **kw: iter(()),  # noqa: ARG005
            check_default_parameters=None,
            check_ruleset_name=None,
            cluster_check_function=None,
            location=PluginLocation(module="<test>", name="<test>"),
        ),
        check_function=check_function,
        get_parameters=dict,
        get_agent_output=get_agent_output,
        get_effective_host=lambda host_name, *_args: host_name,
        snmp_backend=SNMPBackendEnum.CLASSIC,
        debug=False,
    )


def _make_check_plugin() -> CheckPlugin:
    return CheckPlugin(
        name=CheckPluginName("plugin"),
        sections=[ParsedSectionName("section")],
        service_name="Service",
        discovery_function=lambda *_args, **_kw: iter(()),
        discovery_default_parameters=None,
        discovery_ruleset_name=None,
        discovery_ruleset_type="merged",
        check_function=lambda *_args, **_kw: iter(()),
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
                error_handling=lambda *_args, **_kw: "error",
                debug=True,
            ),
            section_plugins={SectionName("section"): SectionPlugin.trivial(SectionName("section"))},
        )
    }


def _get_aggregated_result(
    host_name: HostName,
    service: ConfiguredService,
    check_function: _CheckFunction,
) -> AggregatedResult:
    return checkers.get_aggregated_result(
        host_name,
        False,
        cluster_nodes=(),
        providers=_make_providers(host_name),
        service=service,
        plugin=_make_check_plugin(),
        check_function=check_function,
        get_parameters=lambda: service.parameters.evaluate(lambda _timeperiod: True, debug=True),
        get_agent_output=lambda: None,
        get_effective_host=lambda host_name, _service_name, _labels: host_name,
        snmp_backend=SNMPBackendEnum.CLASSIC,
        debug=False,
    )


def _raise(**_kwargs: object) -> checkers._Subresults:
    raise ValueError("crash")


@pytest.mark.usefixtures("patch_omd_site")
def test_crash_report_of_a_check_function_contains_the_agent_output() -> None:
    _aggregated_result_of(_raise, lambda: AgentRawData(b"<<<uptime>>>\n123\n"))

    assert pop_crash_report_file("check", "agent_output") == b"<<<uptime>>>\n123\n"


def test_agent_output_is_not_requested_if_the_check_function_succeeds() -> None:
    def get_agent_output() -> AgentRawData | None:
        raise AssertionError("agent output requested")

    aggregated = _aggregated_result_of(lambda **_kwargs: _OK_SUBRESULTS, get_agent_output)

    assert aggregated.result == SubmittableServiceCheckResult(0, "OK\nOK", ())


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

    def check_function(**kwargs: object) -> checkers._Subresults:
        received.update(kwargs)
        return _OK_SUBRESULTS

    result = _get_aggregated_result(host_name, _make_service({"levels": (1, 2)}), check_function)

    assert result.result == SubmittableServiceCheckResult(0, "OK\nOK", ())
    assert received["params"] == {"levels": (1, 2)}


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
    monkeypatch.setattr(checkers, "create_check_crash_dump", lambda *_args, **_kw: "crash dump")

    calls: list[Mapping[str, object]] = []

    def check_function(**kwargs: object) -> checkers._Subresults:
        calls.append(kwargs)
        return _OK_SUBRESULTS

    result = _get_aggregated_result(host_name, _make_service(raw_parameters), check_function)

    assert not calls
    assert result.data_received
    assert result.result == SubmittableServiceCheckResult(3, "crash dump")


_SENSORS_SECTION = SectionName("sensors")
_SENSORS_PLUGIN = CheckPluginName("sensors")
_SENSOR_SERVICE = ConfiguredService(
    _SENSORS_PLUGIN,
    "sensor 1",
    ServiceName("Sensor sensor 1"),
    TimespecificParameters(),
    {},
    {},
    {},
    False,
)

type _SensorsSection = Mapping[str, Mapping[str, float | ParseFailure]]


def _parse_sensors(readings: Mapping[str, str]) -> _SensorsSection:
    return {
        "sensor 1": {name: parse_as(float, value, field=name) for name, value in readings.items()}
    }


def _section_with_unparsable_reading() -> _SensorsSection:
    return _parse_sensors({"humidity": "N/A", "temperature": "23.0"})


def _section_with_valid_readings() -> _SensorsSection:
    return _parse_sensors({"humidity": "40.0", "temperature": "23.0"})


def _check_sensor(item: str, section: _SensorsSection) -> CheckResultV3Unstable:
    for name, reading in section[item].items():
        if isinstance(reading, ParseFailure):
            yield reading
        else:
            yield Result(state=State.OK, summary=f"{name.title()}: {reading}")


def _cluster_check_sensor(
    item: str, section: Mapping[str, _SensorsSection | None]
) -> CheckResultV3Unstable:
    for node_section in section.values():
        if node_section is not None:
            yield from _check_sensor(item, node_section)


def _discover_sensors(section: _SensorsSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _sensors_plugin() -> CheckPlugin:
    return create_check_plugin(
        name=str(_SENSORS_PLUGIN),
        sections=[str(_SENSORS_SECTION)],
        service_name="Sensor %s",
        discovery_function=_discover_sensors,
        check_function=_check_sensor,
        cluster_check_function=_cluster_check_sensor,
        location=PluginLocation("not_relevant_for_test", "sensors"),
    )


def _sensors_providers(sections: Mapping[HostName, _SensorsSection]) -> Mapping[HostKey, Provider]:
    return {
        host_key: provider
        for host_name, section in sections.items()
        for host_key, provider in make_providers(
            {HostKey(host_name, SourceType.HOST): HostSections({_SENSORS_SECTION: [["raw"]]})},
            {
                _SENSORS_SECTION: SectionPlugin(
                    supersedes=set(),
                    parse_function=lambda _raw_data, section=section: section,
                    parsed_section_name=ParsedSectionName(str(_SENSORS_SECTION)),
                )
            },
            error_handling=lambda *_args, **_kw: "error",
            debug=False,
        ).items()
    }


def _checked_sensor(
    host_name: HostName,
    sections: Mapping[HostName, _SensorsSection],
    tmp_path: Path,
    cluster_mode: Literal["native", "failover", "worst", "best"] = "native",
    nodes: Sequence[HostName] = (),
    debug: bool = False,
) -> ServiceCheckResult:
    checker = checkers.CheckerPluginMapper(
        checkers.CheckerConfig(
            only_from=lambda _host_name: None,
            effective_service_level=lambda *_args: 0,
            get_clustered_service_configuration=lambda *_args: (cluster_mode, {}),
            nodes=lambda _host_name: nodes,
            effective_host=lambda *_args: host_name,
            get_snmp_backend=lambda _host_name: SNMPBackendEnum.CLASSIC,
            timeperiods_active={},
        ),
        {_SENSORS_PLUGIN: _sensors_plugin()},
        ValueStoreManager(host_name, AllValueStoresStore(tmp_path / "value_store")),
        clusters=(host_name,) if nodes else (),
        get_agent_output=lambda: None,
        omd_root=tmp_path,
        debug=debug,
    )[_SENSORS_PLUGIN]
    return checker.function(
        host_name,
        _SENSOR_SERVICE,
        providers=_sensors_providers(sections),
        is_preview=False,
    ).result


def _crash_info() -> Mapping[str, object]:
    crash_info = pop_crash_report_file("check", "crash.info")
    assert crash_info is not None
    loaded: Mapping[str, object] = json.loads(crash_info)
    return loaded


def _checked_host(section: _SensorsSection, tmp_path: Path) -> ServiceCheckResult:
    return _checked_sensor(HostName("host"), {HostName("host"): section}, tmp_path)


@pytest.mark.usefixtures("patch_omd_site")
def test_an_unparsable_value_turns_only_its_own_subresult_unknown(tmp_path: Path) -> None:
    result = _checked_host(_section_with_unparsable_reading(), tmp_path)
    crash_id = _crash_info()["id"]

    assert result == SubmittableServiceCheckResult(
        3,
        "Could not parse 'humidity': could not convert string to float: 'N/A'(?), "
        "Temperature: 23.0\n"
        "Could not parse 'humidity': could not convert string to float: 'N/A'(?)\n"
        "Temperature: 23.0\n"
        "Could not parse 'humidity' - please submit a crash report! "
        f"(Crash-ID: {crash_id})",
        [],
    )


@pytest.mark.usefixtures("patch_omd_site")
def test_every_unparsable_value_of_a_service_is_shown(tmp_path: Path) -> None:
    result = _checked_host(_parse_sensors({"humidity": "N/A", "temperature": "hot"}), tmp_path)
    _crash_info()

    assert result.state == 3
    assert result.output.split("\n", 1)[0] == (
        "Could not parse 'humidity': could not convert string to float: 'N/A'(?), "
        "Could not parse 'temperature': could not convert string to float: 'hot'(?)"
    )


@pytest.mark.usefixtures("patch_omd_site")
def test_an_unparsable_value_offers_a_crash_report(tmp_path: Path) -> None:
    result = _checked_host(_section_with_unparsable_reading(), tmp_path)

    assert f"(Crash-ID: {_crash_info()['id']})" in result.output


@pytest.mark.usefixtures("patch_omd_site")
def test_the_crash_report_shows_only_in_the_details(tmp_path: Path) -> None:
    summary, details = _checked_host(_section_with_unparsable_reading(), tmp_path).output.split(
        "\n", 1
    )
    _crash_info()

    assert "(Crash-ID: " not in summary
    assert "(Crash-ID: " in details


@pytest.mark.usefixtures("patch_omd_site")
def test_the_crash_report_shows_the_traceback_of_the_parse_error(tmp_path: Path) -> None:
    _checked_host(_section_with_unparsable_reading(), tmp_path)
    crash_info = _crash_info()

    exc_traceback = crash_info["exc_traceback"]
    assert isinstance(exc_traceback, list)

    assert crash_info["exc_type"] == "ValueError"
    assert [frame[2] for frame in exc_traceback] == ["_report_parse_failures", "parse_as"]


@pytest.mark.usefixtures("patch_omd_site")
def test_a_failure_reported_again_has_the_same_traceback(tmp_path: Path) -> None:
    section = _section_with_unparsable_reading()
    _checked_host(section, tmp_path)
    first = _crash_info()["exc_traceback"]

    _checked_host(section, tmp_path)

    assert _crash_info()["exc_traceback"] == first


@pytest.mark.usefixtures("patch_omd_site")
def test_an_unparsable_value_is_raised_in_debug_mode(tmp_path: Path) -> None:
    with pytest.raises(ExceptionGroup) as excinfo:
        _checked_sensor(
            HostName("host"),
            {HostName("host"): _section_with_unparsable_reading()},
            tmp_path,
            debug=True,
        )

    assert [type(exc) for exc in excinfo.value.exceptions] == [ValueError]


def _checked_cluster(
    cluster_mode: Literal["native", "failover", "worst", "best"],
    sections: Mapping[HostName, _SensorsSection],
    tmp_path: Path,
) -> ServiceCheckResult:
    return _checked_sensor(
        HostName("cluster"),
        sections,
        tmp_path,
        cluster_mode,
        nodes=(HostName("node1"), HostName("node2")),
    )


def _checked_cluster_with_both_nodes(
    cluster_mode: Literal["native", "failover", "worst", "best"], tmp_path: Path
) -> ServiceCheckResult:
    return _checked_cluster(
        cluster_mode,
        {
            HostName("node1"): _section_with_unparsable_reading(),
            HostName("node2"): _section_with_valid_readings(),
        },
        tmp_path,
    )


@pytest.mark.usefixtures("patch_omd_site")
def test_an_unparsable_value_on_the_worst_node_turns_the_cluster_unknown(tmp_path: Path) -> None:
    result = _checked_cluster_with_both_nodes("worst", tmp_path)
    _crash_info()

    assert result.state == 3
    assert "Could not parse 'humidity'" in result.output


@pytest.mark.usefixtures("patch_omd_site")
def test_an_unparsable_value_on_an_ignored_node_keeps_the_cluster_state(tmp_path: Path) -> None:
    result = _checked_cluster_with_both_nodes("best", tmp_path)
    _crash_info()

    assert result.state == 0
    assert "Humidity: 40.0" in result.output


@pytest.mark.usefixtures("patch_omd_site")
def test_an_unparsable_value_on_an_ignored_node_offers_a_crash_report(tmp_path: Path) -> None:
    result = _checked_cluster_with_both_nodes("best", tmp_path)

    assert f"(Crash-ID: {_crash_info()['id']})" in result.output


@pytest.mark.usefixtures("patch_omd_site")
def test_an_unparsable_value_on_the_active_failover_node_turns_the_cluster_unknown(
    tmp_path: Path,
) -> None:
    result = _checked_cluster(
        "failover", {HostName("node1"): _section_with_unparsable_reading()}, tmp_path
    )

    assert f"(Crash-ID: {_crash_info()['id']})" in result.output
    assert result.state == 3


@pytest.mark.usefixtures("patch_omd_site")
def test_a_native_cluster_check_function_reports_the_failures_it_yields(tmp_path: Path) -> None:
    result = _checked_cluster_with_both_nodes("native", tmp_path)

    assert f"(Crash-ID: {_crash_info()['id']})" in result.output
    assert result.state == 3
