#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from unittest import mock

import pytest
from pytest_mock import MockerFixture

from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.testlib.unit.utils import reset_registries

import cmk.ccc.resulttype as result
from cmk.ccc.version import edition

from cmk.utils import paths
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui.watolib import activate_changes


def test_wait_for_completion_invalid_activation_id(clients: ClientRegistry) -> None:
    resp = clients.ActivateChanges.request(
        "get",
        url="/objects/activation_run/asdf/actions/wait-for-completion/invoke",
        expect_ok=False,
    )
    resp.assert_status_code(404)
    assert resp.json["detail"] == "Could not find an activation with id 'asdf'."


def test_get_non_existing_activation(clients: ClientRegistry) -> None:
    clients.ActivateChanges.get_activation(
        activation_id="non_existing_activation_id",
        expect_ok=False,
    ).assert_status_code(404)


def test_list_currently_running_activations(clients: ClientRegistry) -> None:
    clients.ActivateChanges.get_running_activations()


def test_activate_changes_unknown_site(clients: ClientRegistry, is_licensed: bool) -> None:
    resp = clients.ActivateChanges.activate_changes(sites=["asdf"], expect_ok=False)
    resp.assert_status_code(400)
    assert "Unknown site" in repr(resp.json), resp.json


@mock.patch("cmk.messaging.rabbitmq.rabbitmqctl_running", lambda: False)
def test_activate_changes(
    mocker: MockerFixture,
    clients: ClientRegistry,
    is_licensed: bool,
    monkeypatch: pytest.MonkeyPatch,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    # NOTE: this test (or any other) must not leave behind a running background job! (even in case of failure)

    # Create a host
    clients.HostConfig.create(host_name="foobar", folder="/")

    # do not start the activation/background job, this doesn't test the "wait-for-completion" endpoint
    mocker.patch(
        "cmk.gui.watolib.activate_changes.ActivateChangesSchedulerBackgroundJob.start",
        return_value=result.OK(None),
    )

    restart_rabbitmq_when_changed = mocker.patch(
        "cmk.gui.watolib.activate_changes.rabbitmq.update_and_activate_rabbitmq_definitions",
    )

    with reset_registries([activate_changes.activation_features_registry]):
        orig_features = activate_changes.activation_features_registry[str(edition(paths.omd_root))]
        activate_changes.activation_features_registry.register(
            activate_changes.ActivationFeatures(
                orig_features.edition,
                sync_file_filter_func=orig_features.sync_file_filter_func,
                snapshot_manager_factory=orig_features.snapshot_manager_factory,
                get_rabbitmq_definitions=orig_features.get_rabbitmq_definitions,
                distribute_piggyback_hub_configs=mocker.MagicMock(),
            ),
        )

        # Activate changes
        with mock_livestatus(expect_status_query=True):
            resp = clients.ActivateChanges.activate_changes()

    # activation_start.assert_called_once()
    restart_rabbitmq_when_changed.assert_called_once()
    assert set(resp.json["extensions"]) == {
        "sites",
        "is_running",
        "force_foreign_changes",
        "time_started",
        "changes",
    }
    assert set(resp.json["extensions"]["changes"][0]) == {
        "id",
        "user_id",
        "action_name",
        "text",
        "time",
    }


def test_list_pending_changes(clients: ClientRegistry) -> None:
    clients.HostConfig.create(host_name="foobar", folder="/")
    resp = clients.ActivateChanges.list_pending_changes()
    assert set(resp.json["value"][0]) == {"id", "user_id", "action_name", "text", "time"}
    assert "actions/activate-changes/invoke" in resp.json["links"][0]["href"]


def test_list_activate_changes_invalid_etag(clients: ClientRegistry) -> None:
    clients.HostConfig.create(host_name="foobar", folder="/")
    resp = clients.ActivateChanges.activate_changes(
        etag="invalid_etag",
        expect_ok=False,
    )
    resp.assert_status_code(412)
    assert resp.json["title"] == "Precondition failed"


def test_list_activate_changes_no_if_match_header(clients: ClientRegistry) -> None:
    clients.HostConfig.create(host_name="foobar", folder="/")
    resp = clients.ActivateChanges.activate_changes(
        etag=None,
        expect_ok=False,
    )
    resp.assert_status_code(428)
    assert resp.json["title"] == "Precondition required"


@mock.patch("cmk.messaging.rabbitmq.rabbitmqctl_running", lambda: False)
def test_list_activate_changes_star_etag(
    mocker: MockerFixture,
    clients: ClientRegistry,
    is_licensed: bool,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    clients.HostConfig.create(host_name="foobar", folder="/")

    activation_start = mocker.patch(
        "cmk.gui.watolib.activate_changes.ActivateChangesManager._start_activation"
    )
    restart_rabbitmq_when_changed = mocker.patch(
        "cmk.gui.watolib.activate_changes.rabbitmq.update_and_activate_rabbitmq_definitions",
    )
    with reset_registries([activate_changes.activation_features_registry]):
        orig_features = activate_changes.activation_features_registry[str(edition(paths.omd_root))]
        activate_changes.activation_features_registry.register(
            activate_changes.ActivationFeatures(
                orig_features.edition,
                sync_file_filter_func=orig_features.sync_file_filter_func,
                snapshot_manager_factory=orig_features.snapshot_manager_factory,
                get_rabbitmq_definitions=orig_features.get_rabbitmq_definitions,
                distribute_piggyback_hub_configs=mocker.MagicMock(),
            ),
        )

        with mock_livestatus(expect_status_query=True):
            clients.ActivateChanges.activate_changes(etag="star")
    activation_start.assert_called_once()
    restart_rabbitmq_when_changed.assert_called_once()


@mock.patch("cmk.messaging.rabbitmq.rabbitmqctl_running", lambda: False)
def test_list_activate_changes_valid_etag(
    mocker: MockerFixture,
    clients: ClientRegistry,
    is_licensed: bool,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    clients.HostConfig.create(host_name="foobar", folder="/")

    activation_start = mocker.patch(
        "cmk.gui.watolib.activate_changes.ActivateChangesManager._start_activation"
    )
    restart_rabbitmq_when_changed = mocker.patch(
        "cmk.gui.watolib.activate_changes.rabbitmq.update_and_activate_rabbitmq_definitions",
    )
    with reset_registries([activate_changes.activation_features_registry]):
        orig_features = activate_changes.activation_features_registry[str(edition(paths.omd_root))]
        activate_changes.activation_features_registry.register(
            activate_changes.ActivationFeatures(
                orig_features.edition,
                sync_file_filter_func=orig_features.sync_file_filter_func,
                snapshot_manager_factory=orig_features.snapshot_manager_factory,
                get_rabbitmq_definitions=orig_features.get_rabbitmq_definitions,
                distribute_piggyback_hub_configs=mocker.MagicMock(),
            ),
        )
        with mock_livestatus(expect_status_query=True):
            clients.ActivateChanges.activate_changes(etag="valid_etag")
    activation_start.assert_called_once()
    restart_rabbitmq_when_changed.assert_called_once()
