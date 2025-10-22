#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import io
import tarfile
from datetime import datetime, UTC
from pathlib import Path

from cmk.agent_receiver.config import get_config
from cmk.agent_receiver.log import bound_contextvars
from cmk.agent_receiver.relay.api.routers.tasks.libs.retrieve_config_serial import (
    retrieve_config_serial,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayConfigSpec,
    RelayTask,
    TasksRepository,
    TaskStatus,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.relay_protocols.configuration import CONFIG_ARCHIVE_ROOT_FOLDER_NAME


@dataclasses.dataclass
class ConfigTaskFactory:
    relays_repository: RelaysRepository
    tasks_repository: TasksRepository

    def create_for_all_relays(self) -> list[RelayTask]:
        """
        Creates relay config tasks for all registered relays.
        The number of actually created task might be lower than the number of the relays,
        because some relays might already have existing pending tasks for the current serial value.
        """
        relay_ids = self.relays_repository.get_all_relay_ids()
        return self._create(relay_ids)

    def create_for_relay(self, relay_id: RelayID) -> RelayTask | None:
        """
        Creates a relay config task for the specified relay.
        If the relay has already a pending relay for the current serial value, the function
        does nothing and returns None.
        """
        result = self._create([relay_id])
        return None if not result else result[0]

    def _create(self, relay_ids: list[RelayID]) -> list[RelayTask]:
        now = datetime.now(UTC)
        created_tasks: list[RelayTask] = []
        serial = retrieve_config_serial()
        config = get_config()

        for rid in relay_ids:
            # TODO This check should be performed in TasksRepository, when saving
            if self._pending_configuration_task_exists(rid, serial):
                continue  # Skip creating duplicate pending tasks
            parent = config.helper_config_dir / f"{serial}/relays/{rid}"
            relay_config_spec = RelayConfigSpec(serial=serial, tar_data=create_tar(parent))
            task = RelayTask(spec=relay_config_spec, creation_timestamp=now, update_timestamp=now)
            with bound_contextvars(task_id=task.id):
                self.tasks_repository.store_task(rid, task)
                created_tasks.append(task)
        return created_tasks

    def _pending_configuration_task_exists(
        self,
        relay_id: RelayID,
        serial: str,
    ) -> bool:
        tasks = self.tasks_repository.get_tasks(relay_id)
        return any(
            task.status == TaskStatus.PENDING
            and isinstance(task.spec, RelayConfigSpec)
            and task.spec.serial == serial
            for task in tasks
        )


def create_tar(parent: Path) -> bytes:
    """Create an uncompressed tar archive in memory preserving structure from common parent.

    This function creates an uncompressed tar archive containing the specified folder
    with its directory structure preserved. The paths in the archive are relative
    to the specified common parent directory. The common parent directory will be
    renamed to "config" in the archive

    Args:
        common_parent: The common parent directory. Paths in the archive will be
                      relative to this directory.

    Returns:
        The content of the tar archive as bytes.

    Example:
        >>> files = [
        ...     '/home/user/project/src/main.py',
        ...     '/home/user/project/src/utils.py',
        ...     '/home/user/project/tests/test_main.py'
        ... ]
        >>> base64_tar = create_tar('/home/user/project')
        >>> # Archive will contain:
        >>> # config/src/main.py
        >>> # config/src/utils.py
        >>> # config/tests/test_main.py
    """

    # Create an in-memory bytes buffer
    tar_buffer = io.BytesIO()

    # Create tar archive in memory
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        tar.add(parent, arcname=CONFIG_ARCHIVE_ROOT_FOLDER_NAME)

    # Get the binary content of the tar archive
    return tar_buffer.getvalue()
