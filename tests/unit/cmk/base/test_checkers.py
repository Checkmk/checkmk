#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import socket
import sys
import time
from collections.abc import Iterable, Mapping
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
from cmk.agent_based.v3_unstable import Metric as MetricV3Unstable
from cmk.base import checkers
from cmk.base.checkers import CMKFetcher
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.ccc import resulttype as result
from cmk.ccc.exceptions import MKTimeout, OnError
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.checkerplugin import ConfiguredService
from cmk.checkengine.fetcher_abc import Mode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetcher_utils.trigger import PlainFetcherTrigger
from cmk.checkengine.fetchers.snmp import (
    NoSelectedSNMPSections,
    SNMPFetcherConfig,
)
from cmk.checkengine.filecache import FileCacheOptions
from cmk.checkengine.helper_interface import FetcherType, HostKey, SourceInfo, SourceType
from cmk.checkengine.parser import HostSections
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName, FinalCheckResult
from cmk.checkengine.specs.checkresults import (
    MetricTuple,
    ServiceCheckResult,
    SubmittableServiceCheckResult,
)
from cmk.checkengine.specs.exitspec import ExitSpec
from cmk.checkengine.specs.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.summarize import SummaryConfig
from cmk.piggyback.backend import Config as PiggybackConfig
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
        checkers._aggregate_results(checkers._consume_check_results(subresults))  # noqa: SLF001
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
    _, perfdata, _ = checkers._consume_check_results(  # noqa: SLF001
        [MetricV3Unstable("m", 1.0, levels=(float("inf"), float("-inf")))]
    )
    assert len(perfdata) == 1
    assert perfdata[0].warn == sys.float_info.max
    assert perfdata[0].crit == -sys.float_info.max


def test_consume_check_results_clamps_inf_lower_levels() -> None:
    _, perfdata, _ = checkers._consume_check_results(  # noqa: SLF001
        [
            MetricV3Unstable(
                "m",
                1.0,
                lower_levels=(float("inf"), float("-inf")),
            )
        ]
    )
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
    )

    fetched = fetcher(testhost, ip_address=None)

    agent_sources = [(source, res) for source, res, _snapshot in fetched if source.ident == "agent"]
    assert len(agent_sources) == 1
    source, res = agent_sources[0]
    assert source.ipaddress is None
    assert source.fetcher_type is FetcherType.NONE
    assert res.is_error()
