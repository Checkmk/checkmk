#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import (
    ConfigTaskAlreadyExists,
    ConfigTaskCreationFailed,
    ConfigTaskFactory,
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


def test_create_task_for_single_chosen_relay_when_relay_folder_does_not_exist(
    config_task_factory: ConfigTaskFactory,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
    site_context: Config,
) -> None:
    """
    Should not create a task for the specified relay when the relay folder is not created (yet).
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

    # If we don't have a relay folder for relay 2 for this serial...

    _ = create_config_folder(site_context.omd_root, [relay_id_1, relay_id_3])

    # ...then we cannot create tasks for chosen relay: relay_id_2

    creation_result = config_task_factory.create_for_relay(relay_id_2)
    assert isinstance(creation_result, ConfigTaskCreationFailed)

    # assert no tasks are created for the other relays

    assert len(tasks_repository.get_tasks(relay_id_1)) == 0
    assert len(tasks_repository.get_tasks(relay_id_3)) == 0
