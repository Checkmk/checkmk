#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Iterable, Mapping
from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName

from cmk.utils.servicename import ServiceName

from cmk.checkengine.checkresults import ServiceCheckResult, SubmittableServiceCheckResult
from cmk.checkengine.fetcher import HostKey, SourceType
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.plugins import CheckPluginName, ConfiguredService

from cmk.base import checkers

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    PredictionInfo,
    PredictionParameters,
)
from cmk.agent_based.v1 import Metric, Result, State
from cmk.agent_based.v2 import CheckResult


def make_timespecific_params_list(
    entries: Iterable[Mapping[str, object]],
) -> TimespecificParameters:
    return TimespecificParameters([TimespecificParameterSet.from_parameters(e) for e in entries])


def make_service(desription: ServiceName) -> ConfiguredService:
    return ConfiguredService(
        CheckPluginName("dummy"), None, desription, TimespecificParameters(), {}, {}, {}, False
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
