#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name
import json

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based import kube_collector_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.utils.kube import (
    CheckmkKubeAgentMetadata,
    ClusterCollectorMetadata,
    CollectorComponentsMetadata,
    CollectorHandlerLog,
    CollectorProcessingLogs,
    CollectorState,
    CollectorType,
    NodeComponent,
    NodeMetadata,
    PlatformMetadata,
)


class ClusterCollectorMetadataFactory(ModelFactory):
    __model__ = ClusterCollectorMetadata


class NodeMetadataFactory(ModelFactory):
    __model__ = NodeMetadata


@pytest.fixture
def component_handling_state() -> CollectorState:
    return CollectorState.OK


@pytest.fixture
def collector_metadata_handling_state() -> CollectorState:
    return CollectorState.OK


@pytest.fixture
def metadata_collection_log(
    collector_metadata_handling_state: CollectorState,
) -> CollectorHandlerLog:
    return CollectorHandlerLog(
        status=collector_metadata_handling_state, title="title", detail="detail"
    )


@pytest.fixture
def collector_handling_logs(component_handling_state: CollectorState) -> CollectorProcessingLogs:
    return CollectorProcessingLogs(
        container=CollectorHandlerLog(status=component_handling_state, title="title", detail="OK"),
        machine=CollectorHandlerLog(status=component_handling_state, title="title", detail="OK"),
    )


@pytest.fixture
def collectors_metadata(
    metadata_collection_log: CollectorHandlerLog,
    collector_metadata_handling_state: CollectorState,
) -> CollectorComponentsMetadata:
    return CollectorComponentsMetadata(
        processing_log=metadata_collection_log,
        cluster_collector=ClusterCollectorMetadataFactory.build(),
        node_collectors=[NodeMetadataFactory.build()],
    )


def test_parse_collector_metadata():
    string_table_element = json.dumps(
        {
            "processing_log": {"status": "ok", "title": "title", "detail": "detail"},
            "cluster_collector": {
                "node": "node",
                "host_name": "host",
                "container_platform": {
                    "os_name": "os",
                    "os_version": "version",
                    "python_version": "pversion",
                    "python_compiler": "compiler",
                },
                "checkmk_kube_agent": {"project_version": "package"},
            },
            "node_collectors": [
                {
                    "name": "minikube",
                    "components": {
                        "checkmk_agent_version": {
                            "collector_type": "Machine Sections",
                            "checkmk_kube_agent": {"project_version": "0.1.0"},
                            "name": "checkmk_agent_version",
                            "version": "version",
                        },
                    },
                }
            ],
        }
    )
    assert kube_collector_info.parse_collector_metadata(
        [[string_table_element]]
    ) == CollectorComponentsMetadata(
        processing_log=CollectorHandlerLog(
            status=CollectorState.OK, title="title", detail="detail"
        ),
        cluster_collector=ClusterCollectorMetadata(
            node="node",
            host_name="host",
            container_platform=PlatformMetadata(
                os_name="os",
                os_version="version",
                python_version="pversion",
                python_compiler="compiler",
            ),
            checkmk_kube_agent=CheckmkKubeAgentMetadata(project_version="package"),
        ),
        node_collectors=[
            NodeMetadata(
                name="node",
                components={
                    "checkmk_agent_version": NodeComponent(
                        collector_type=CollectorType.MACHINE_SECTIONS,
                        checkmk_kube_agent=CheckmkKubeAgentMetadata(project_version="package"),
                        name="checkmk_agent_version",
                        version="version",
                    ),
                },
            )
        ],
    )


def test_parse_collector_components():
    string_table_element = json.dumps(
        {
            "container": {"status": "ok", "title": "title", "detail": "detail"},
            "machine": {"status": "ok", "title": "title", "detail": "detail"},
        }
    )
    assert kube_collector_info.parse_collector_processing_logs(
        [[string_table_element]]
    ) == CollectorProcessingLogs(
        container=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="detail"),
        machine=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="detail"),
    )


def test_check_all_ok_sections(collectors_metadata, collector_handling_logs):
    check_result = list(
        kube_collector_info.check(
            collectors_metadata,
            collector_handling_logs,
        )
    )
    assert len(check_result) == 4
    assert all(isinstance(result, Result) for result in check_result)
    assert all(result.state == State.OK for result in check_result if isinstance(result, Result))


def test_check_with_no_collector_components_section(collectors_metadata):
    check_result = list(kube_collector_info.check(collectors_metadata, None))
    assert all(isinstance(result, Result) for result in check_result)
    assert isinstance(check_result[0], Result) and check_result[0].summary.startswith(
        "Cluster collector version:"
    )
    assert len(check_result) == 2


@pytest.mark.parametrize("collector_metadata_handling_state", [CollectorState.ERROR])
def test_check_with_errored_handled_metadata_section(collectors_metadata, collector_handling_logs):
    check_result = list(kube_collector_info.check(collectors_metadata, collector_handling_logs))
    assert len(check_result) == 1
    assert isinstance(check_result[0], Result) and check_result[0].state == State.CRIT


@pytest.mark.parametrize("component_handling_state", [CollectorState.ERROR])
def test_check_with_errored_handled_component_section(collector_handling_logs):
    result = list(
        kube_collector_info._component_check("Container Metrics", collector_handling_logs.container)
    )
    assert len(result) == 1
    assert result[0].state == State.OK
    assert result[0].summary.startswith("Container Metrics: ")
