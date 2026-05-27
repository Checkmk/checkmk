#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from netapp_ontap import resources as NetAppResource
from netapp_ontap.error import NetAppRestError

from cmk.plugins.netapp import models
from cmk.plugins.netapp.special_agent.agent_netapp_ontap import (
    agent_netapp_main,
    fetch_aggr,
    get_nodes,
    parse_arguments,
)

_MODULE = "cmk.plugins.netapp.special_agent.agent_netapp_ontap"


class _AuthError(NetAppRestError):
    """NetAppRestError with status_code 401 for testing authentication failures."""

    def __init__(self) -> None:
        Exception.__init__(self, "401 Unauthorized")

    @property
    def status_code(self) -> int:
        return 401


class _ServerError(NetAppRestError):
    """NetAppRestError with a non-auth status code for testing other API failures."""

    def __init__(self) -> None:
        Exception.__init__(self, "503 Service Unavailable")

    @property
    def status_code(self) -> int:
        return 503


def test_agent_exits_1_when_connection_returns_401(capsys: pytest.CaptureFixture[str]) -> None:
    """When the NetApp API returns a 401 auth error, agent_netapp_main should return 1.

    Regression: after c6bf4fe, safe_write_section catches all exceptions including
    NetAppRestError(401), so the error never reaches the 401 handler in agent_netapp_main
    and the agent returns 0 instead of 1.
    """
    args = parse_arguments(
        [
            "--hostname",
            "myhost",
            "--username",
            "admin",
            "--password",
            "secret",
            "--no-cert-check",
            "--fetched-resources",
            "node",
        ]
    )

    with (
        patch("cmk.plugins.netapp.special_agent.agent_netapp_ontap.HostConnection") as mock_conn,
        patch.object(NetAppResource.Node, "get_collection", side_effect=_AuthError()),
    ):
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        result = agent_netapp_main(args)

    assert result == 1
    assert "Authentication failed" in capsys.readouterr().err


def test_agent_does_not_exit_1_when_connection_returns_non_auth_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-401 API error (e.g. 503) should not cause agent_netapp_main to return 1.
    The error is written as an error section and the agent exits cleanly with 0.
    """
    args = parse_arguments(
        [
            "--hostname",
            "myhost",
            "--username",
            "admin",
            "--password",
            "secret",
            "--no-cert-check",
            "--fetched-resources",
            "node",
        ]
    )

    with (
        patch("cmk.plugins.netapp.special_agent.agent_netapp_ontap.HostConnection") as mock_conn,
        patch.object(NetAppResource.Node, "get_collection", side_effect=_ServerError()),
    ):
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        result = agent_netapp_main(args)

    assert result == 0
    assert "Authentication failed" not in capsys.readouterr().err


_CLUSTER_VERSION = models.Version(generation=9, major=12, minor=1)
_NODE_VERSION_OLD = models.Version(generation=9, major=11, minor=0)
_NODE_VERSION_NEW = models.Version(generation=9, major=12, minor=1)
_FETCHED_RESOURCES_NODE: set[str] = {"node"}


def _make_node(version: models.Version) -> MagicMock:
    node = MagicMock()
    node.version = version
    return node


def test_get_nodes_empty_nodes_falls_back_to_cluster_version() -> None:
    """When fetch_nodes returns empty, get_nodes falls back to the cluster endpoint
    and returns (None, cluster_version) — no empty node section is written.
    """
    with (
        patch(f"{_MODULE}.fetch_nodes", return_value=iter([])),
        patch(f"{_MODULE}.get_version_from_cluster", return_value=_CLUSTER_VERSION),
        patch(f"{_MODULE}._write_error") as mock_write_error,
    ):
        nodes, version = get_nodes(MagicMock(), MagicMock(), _FETCHED_RESOURCES_NODE)

    assert nodes is None
    assert version == _CLUSTER_VERSION
    mock_write_error.assert_not_called()


def test_get_nodes_empty_nodes_cluster_also_fails() -> None:
    """When both the nodes API and cluster endpoint fail, get_nodes returns (None, None)
    and writes an error section.
    """
    with (
        patch(f"{_MODULE}.fetch_nodes", return_value=iter([])),
        patch(f"{_MODULE}.get_version_from_cluster", side_effect=Exception("cluster down")),
        patch(f"{_MODULE}._write_error") as mock_write_error,
    ):
        nodes, version = get_nodes(MagicMock(), MagicMock(), _FETCHED_RESOURCES_NODE)

    assert nodes is None
    assert version is None
    mock_write_error.assert_called_once()


def test_get_nodes_returns_nodes_and_oldest_version() -> None:
    """When fetch_nodes returns multiple nodes, get_nodes picks the oldest version."""
    node_old = _make_node(_NODE_VERSION_OLD)
    node_new = _make_node(_NODE_VERSION_NEW)

    with (
        patch(f"{_MODULE}.fetch_nodes", return_value=iter([node_old, node_new])),
        patch(f"{_MODULE}.get_version_from_cluster") as mock_cluster,
    ):
        nodes, version = get_nodes(MagicMock(), MagicMock(), _FETCHED_RESOURCES_NODE)

    assert nodes == [node_old, node_new]
    assert version == _NODE_VERSION_OLD
    mock_cluster.assert_not_called()


def _connection_with_cli_response(response_json: dict[str, object] | Exception) -> MagicMock:
    """Fake HostConnection whose CLI passthrough returns ``response_json`` (or raises it).

    HostConnection is a third-party network boundary, so it is stubbed rather than faked.
    """
    connection = MagicMock()
    connection.origin = "https://myhost"
    if isinstance(response_json, Exception):
        connection.session.get.side_effect = response_json
    else:
        connection.session.get.return_value.json.return_value = response_json
    return connection


class _FakeAggregate:
    _collection_uuids: tuple[str, ...] = ()

    def __init__(self, uuid: str) -> None:
        self._uuid = uuid

    @classmethod
    def get_collection(cls, *, connection: object, fields: str) -> "Iterator[_FakeAggregate]":  # noqa: ARG003 (unused class method arg)
        return (cls(uuid) for uuid in cls._collection_uuids)

    def get(self, fields: str) -> None:
        """No remote fetch in the test double; the resource is already populated."""

    def to_dict(self) -> dict[str, object]:
        return {
            "uuid": self._uuid,
            "name": self._uuid,
            "space": {"block_storage": {"available": 1000, "size": 2000}},
        }


def test_fetch_aggr_classic_ontap_discovers_data_and_root_aggregates() -> None:
    """
    Classic ONTAP: the standard collection yields the non-root aggregates and the CLI
    passthrough adds the root aggregates, so every aggregate is monitored.
    """
    connection = _connection_with_cli_response(
        {"records": [{"uuid": "data-1"}, {"uuid": "data-2"}, {"uuid": "root-1"}]}
    )
    args = argparse.Namespace(timeout=30)

    with (
        patch.object(NetAppResource, "Aggregate", _FakeAggregate),
        patch.object(_FakeAggregate, "_collection_uuids", ("data-1", "data-2")),
    ):
        discovered = list(fetch_aggr(connection, args))

    assert {aggregate.name for aggregate in discovered} == {"data-1", "data-2", "root-1"}


def test_fetch_aggr_asa_r2_discovers_data_aggregates() -> None:
    """
    ASA r2: the CLI passthrough rejects the 'uuid' field and returns no records, so the
    data aggregates from the standard collection are monitored (previously none were).
    """
    connection = _connection_with_cli_response(
        {"error": {"message": 'The value "uuid" is invalid for field "fields"', "code": "262197"}}
    )
    args = argparse.Namespace(timeout=30)

    with (
        patch.object(NetAppResource, "Aggregate", _FakeAggregate),
        patch.object(_FakeAggregate, "_collection_uuids", ("dataFA-1", "dataFA-2")),
    ):
        discovered = list(fetch_aggr(connection, args))

    assert {aggregate.name for aggregate in discovered} == {"dataFA-1", "dataFA-2"}


def test_fetch_aggr_continues_when_cli_passthrough_fails() -> None:
    """
    If the CLI passthrough request itself fails, the data aggregates from the standard
    collection are still monitored instead of the whole aggregate fetch failing.
    """
    connection = _connection_with_cli_response(OSError("connection reset"))
    args = argparse.Namespace(timeout=30)

    with (
        patch.object(NetAppResource, "Aggregate", _FakeAggregate),
        patch.object(_FakeAggregate, "_collection_uuids", ("dataFA-1",)),
    ):
        discovered = list(fetch_aggr(connection, args))

    assert {aggregate.name for aggregate in discovered} == {"dataFA-1"}
