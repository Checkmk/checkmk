#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import dataclasses
import io
import tarfile
from datetime import datetime, UTC
from pathlib import Path

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
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth


@dataclasses.dataclass
class ConfigTaskFactory:
    relays_repository: RelaysRepository
    tasks_repository: TasksRepository

    def process(self) -> list[RelayTask]:
        now = datetime.now(UTC)
        created_tasks: list[RelayTask] = []
        auth = InternalAuth()
        serial = retrieve_config_serial()
        relay_config_spec = self._generate_relay_config_spec(serial)
        for relay_id in self.relays_repository.get_all_relay_ids(auth):
            if self._pending_configuration_task_exists(relay_id, serial):
                continue  # Skip creating duplicate pending tasks
            task = RelayTask(spec=relay_config_spec, creation_timestamp=now, update_timestamp=now)
            with bound_contextvars(task_id=task.id):
                self.tasks_repository.store_task(relay_id, task)
                created_tasks.append(task)
        return created_tasks

    def _generate_relay_config_spec(self, serial: str) -> RelayConfigSpec:
        # TODO: Read filesystem and create tar data
        tar_data = ""
        return RelayConfigSpec(serial=serial, tar_data=tar_data)

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


def create_tar_with_structure_as_base64(file_paths: list[Path], common_parent: Path) -> str:
    """Create an uncompressed tar archive in memory preserving structure from common parent.

    This function creates an uncompressed tar archive containing the specified files
    with their directory structure preserved. The paths in the archive are relative
    to the specified common parent directory.

    Args:
        file_paths: List of file paths to include in the tar archive.
                   All files must be under the common_parent directory.
        common_parent: The common parent directory. Paths in the archive will be
                      relative to this directory.

    Returns:
        Base64-encoded string representation of the uncompressed tar archive.

    Raises:
        ValueError: If the file list is empty or a file is not under common_parent.
        FileNotFoundError: If any of the specified files doesn't exist.

    Example:
        >>> files = [
        ...     '/home/user/project/src/main.py',
        ...     '/home/user/project/src/utils.py',
        ...     '/home/user/project/tests/test_main.py'
        ... ]
        >>> base64_tar = create_tar_with_structure_as_base64(files, '/home/user/project')
        >>> # Archive will contain:
        >>> # src/main.py
        >>> # src/utils.py
        >>> # tests/test_main.py
    """
    if not file_paths:
        raise ValueError("File list cannot be empty")

    # Convert common parent to Path object and resolve it
    common_parent_path = Path(common_parent).resolve()

    if not common_parent_path.exists():
        raise FileNotFoundError(f"Common parent directory not found: {common_parent_path}")

    # Convert all paths to Path objects and resolve them
    paths = [Path(fp).resolve() for fp in file_paths]

    # Verify all files exist and are under the common parent
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Check if file is under the common parent
        try:
            path.relative_to(common_parent_path)
        except ValueError:
            raise ValueError(
                f"File {path} is not under common parent directory {common_parent_path}"
            )

    # Create an in-memory bytes buffer
    tar_buffer = io.BytesIO()

    # Create tar archive in memory
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for path in paths:
            # Calculate the relative path from the common parent
            arcname = path.relative_to(common_parent_path)

            # Add file to tar archive with the relative path
            tar.add(path, arcname=str(arcname))

    # Get the binary content of the tar archive
    tar_binary = tar_buffer.getvalue()

    # Convert binary content to base64 string
    base64_string = base64.b64encode(tar_binary).decode("ascii")

    return base64_string
