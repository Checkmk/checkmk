#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import logging
from unittest.mock import patch

from pytest import LogCaptureFixture

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import (
    ConfigTaskAlreadyExists,
    ConfigTaskCreated,
    ConfigTaskCreationFailed,
    ConfigTaskFactory,
    ConfigTaskSkipped,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayConfigSpec,
    RelayTask,
    TasksRepository,
    TaskStatus,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.relay import random_relay_id


def test_create_tasks_for_all_relays(
    config_task_factory: ConfigTaskFactory,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
    site_context: Config,
) -> None:
    # Register two relays
    relay_id_1 = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay-1"
    )
    relay_id_2 = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay-2"
    )

    cf = create_config_folder(site_context.omd_root, [relay_id_1, relay_id_2])

    # Create tasks for all relays
    config_task_factory.create_for_all_relays()

    # assert
    tasks_for_relay_1 = tasks_repository.get_tasks(relay_id_1)
    tasks_for_relay_2 = tasks_repository.get_tasks(relay_id_2)

    assert len(tasks_for_relay_1) == 1
    assert isinstance(tasks_for_relay_1[0].spec, RelayConfigSpec)
    assert tasks_for_relay_1[0].spec.serial == cf.serial

    assert len(tasks_for_relay_2) == 1
    assert isinstance(tasks_for_relay_2[0].spec, RelayConfigSpec)
    assert tasks_for_relay_2[0].spec.serial == cf.serial

    cf.assert_tar_content(relay_id_1, tasks_for_relay_1[0].spec.tar_data)
    cf.assert_tar_content(relay_id_2, tasks_for_relay_2[0].spec.tar_data)


def test_create_task_for_single_chosen_relay_when_no_pending_task(
    config_task_factory: ConfigTaskFactory,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
    site_context: Config,
) -> None:
    """
    Should create a task for the specified relay only, and only if there is no pending task already.
    """

    # Register more relays
    relay_id_1 = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay-1"
    )
    relay_id_2 = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay-2"
    )
    relay_id_3 = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay-3"
    )

    cf = create_config_folder(site_context.omd_root, [relay_id_1, relay_id_2, relay_id_3])

    # Create tasks for chosen relay: relay_id_2
    _ = config_task_factory.create_for_relay(relay_id_2)

    # assert no tasks are created for the other relays

    assert len(tasks_repository.get_tasks(relay_id_1)) == 0
    assert len(tasks_repository.get_tasks(relay_id_3)) == 0

    # assert that the task has been created for relay_id_2

    tasks_for_relay_2 = tasks_repository.get_tasks(relay_id_2)

    assert len(tasks_for_relay_2) == 1
    assert isinstance(tasks_for_relay_2[0].spec, RelayConfigSpec)
    assert tasks_for_relay_2[0].spec.serial == cf.serial

    cf.assert_tar_content(relay_id_2, tasks_for_relay_2[0].spec.tar_data)


def test_create_task_for_single_chosen_relay_when_pending_task(
    config_task_factory: ConfigTaskFactory,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
    site_context: Config,
) -> None:
    """
    Should not create a task for the specified relay when there is pending task already.
    """

    # Register more relays
    relay_id_1 = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay-1"
    )
    relay_id_2 = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay-2"
    )
    relay_id_3 = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay-3"
    )

    cf = create_config_folder(site_context.omd_root, [relay_id_1, relay_id_2, relay_id_3])

    # If we already have a pending task for this serial...

    now = datetime.datetime.now(tz=datetime.UTC)

    stored_task = RelayTask(
        creation_timestamp=now,
        update_timestamp=now,
        status=TaskStatus.PENDING,
        spec=RelayConfigSpec(serial=cf.serial, tar_data=b"some-data"),
    )
    tasks_repository.store_task(relay_id_2, stored_task)

    # ...then we cannot create tasks for chosen relay: relay_id_2
    creation_result = config_task_factory.create_for_relay(relay_id_2)
    assert isinstance(creation_result, ConfigTaskAlreadyExists)

    # assert no tasks are created for the other relays

    assert len(tasks_repository.get_tasks(relay_id_1)) == 0
    assert len(tasks_repository.get_tasks(relay_id_3)) == 0

    # assert that the task has been created for relay_id_2

    tasks_for_relay_2 = tasks_repository.get_tasks(relay_id_2)

    # only the already stored task is there

    assert len(tasks_for_relay_2) == 1
    assert tasks_for_relay_2[0] == stored_task


def test_create_task_for_single_relay_skipped_when_config_not_applied(
    config_task_factory: ConfigTaskFactory,
    site_context: Config,
    caplog: LogCaptureFixture,
) -> None:
    """
    Should skip task creation for a single relay when relay configuration
    is not applied yet (relay_config_applied returns False).

    Tests create_for_relay() with a relay ID that has no config folder.

    Verifies that:
    - ConfigTaskSkipped is returned
    - A DEBUG level log message is emitted indicating the relay is skipped
    - No ERROR level logs are produced
    """

    # Create a minimal config folder to establish the serial
    # Use a relay ID that won't conflict with other tests
    _ = create_config_folder(site_context.omd_root, [])

    # Use a relay ID that has NO config folder
    # This simulates calling create_for_relay for a relay that hasn't been configured yet
    relay_id_without_config = random_relay_id()

    # Capture logs at DEBUG level
    with caplog.at_level(logging.DEBUG, logger="agent-receiver"):
        # When creating a task for a relay without config applied
        creation_result = config_task_factory.create_for_relay(relay_id_without_config)

    # Then it should be skipped
    assert isinstance(creation_result, ConfigTaskSkipped)
    assert creation_result.relay_id == relay_id_without_config

    # Verify DEBUG log message was emitted
    expected_log_msg = f"Skipping config task creation for relay {relay_id_without_config}"
    assert any(expected_log_msg in record.message for record in caplog.records), (
        f"Expected log message not found. Captured logs: {[r.message for r in caplog.records]}"
    )

    # Verify no ERROR or CRITICAL logs were produced
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert not error_logs, (
        f"Expected no ERROR/CRITICAL logs, but found: {[r.message for r in error_logs]}"
    )


def test_create_tasks_for_all_relays_with_multiple_configured_relays(
    config_task_factory: ConfigTaskFactory,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
    site_context: Config,
    caplog: LogCaptureFixture,
) -> None:
    """
    Should create tasks for all relays that have config applied.

    Tests create_for_all_relays() with multiple configured relays.
    Note: get_all_relay_ids() only returns relays with config folders,
    so all relays returned will have relay_config_applied() == True.

    Verifies that:
    - Tasks are created for all configured relays
    - Results are returned for all relays
    - No ERROR level logs are produced
    """

    # Register three relays and create config folders for all of them
    relay_id_1 = relays_repository.add_relay(test_user, relay_id=random_relay_id(), alias="relay-1")
    relay_id_2 = relays_repository.add_relay(test_user, relay_id=random_relay_id(), alias="relay-2")
    relay_id_3 = relays_repository.add_relay(test_user, relay_id=random_relay_id(), alias="relay-3")

    # Create config folders for all relays
    cf = create_config_folder(site_context.omd_root, [relay_id_1, relay_id_2, relay_id_3])

    # Capture logs at DEBUG level
    with caplog.at_level(logging.DEBUG, logger="agent-receiver"):
        # When creating tasks for all relays
        results = config_task_factory.create_for_all_relays()

    # Then we should have results for all relays (get_all_relay_ids returns these 3)
    assert len(results) == 3

    # Verify all relays got tasks created
    assert any(isinstance(r, ConfigTaskCreated) and r.relay_id == relay_id_1 for r in results)
    assert any(isinstance(r, ConfigTaskCreated) and r.relay_id == relay_id_2 for r in results)
    assert any(isinstance(r, ConfigTaskCreated) and r.relay_id == relay_id_3 for r in results)

    # Verify tasks exist for all relays
    for relay_id in [relay_id_1, relay_id_2, relay_id_3]:
        tasks = tasks_repository.get_tasks(relay_id)
        assert len(tasks) == 1
        assert isinstance(tasks[0].spec, RelayConfigSpec)
        assert tasks[0].spec.serial == cf.serial

    # Verify no ERROR or CRITICAL logs were produced
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert not error_logs, (
        f"Expected no ERROR/CRITICAL logs, but found: {[r.message for r in error_logs]}"
    )


def test_create_task_fails_when_tar_creation_raises_exception(
    config_task_factory: ConfigTaskFactory,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
    site_context: Config,
) -> None:
    """
    Should return ConfigTaskCreationFailed when relay configuration is applied
    but tar creation fails due to an exception (e.g., file system error).
    """

    # Register a relay
    relay_id = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay"
    )

    # Create config folder so relay_config_applied returns True
    _ = create_config_folder(site_context.omd_root, [relay_id])

    # Mock create_tar to raise an exception
    with patch(
        "cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory.create_tar"
    ) as mock_create_tar:
        mock_create_tar.side_effect = OSError("Permission denied")

        # When creating a task and tar creation fails
        creation_result = config_task_factory.create_for_relay(relay_id)

        # Then it should return ConfigTaskCreationFailed
        assert isinstance(creation_result, ConfigTaskCreationFailed)
        assert creation_result.relay_id == relay_id
        assert isinstance(creation_result.exception, OSError)
        assert "Permission denied" in str(creation_result.exception)

        # And no task should be stored
        assert len(tasks_repository.get_tasks(relay_id)) == 0
