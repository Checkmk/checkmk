#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from datetime import datetime, UTC

from cmk.agent_receiver.config import get_config
from cmk.agent_receiver.log import bound_contextvars, logger
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayConfigSpec,
    RelayTask,
    TasksRepository,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth


class GetConfigSerialError(Exception):
    pass


@dataclasses.dataclass
class ActivateConfigHandler:
    relays_repository: RelaysRepository
    tasks_repository: TasksRepository

    def process(self) -> list[RelayTask]:
        now = datetime.now(UTC)
        created_tasks: list[RelayTask] = []
        auth = InternalAuth()
        serial = self._get_config_serial()
        relay_config_spec = self._generate_relay_config_spec(serial)
        for relay_id in self.relays_repository.get_all_relay_ids(auth):
            task = RelayTask(spec=relay_config_spec, creation_timestamp=now, update_timestamp=now)
            with bound_contextvars(task_id=task.id):
                self.tasks_repository.store_task(relay_id, task)
                created_tasks.append(task)
        return created_tasks

    def _generate_relay_config_spec(self, serial: str) -> RelayConfigSpec:
        # TODO: Read filesystem and create tar data
        tar_data = ""
        return RelayConfigSpec(serial=serial, tar_data=tar_data)

    def _get_config_serial(self) -> str:
        """
        Determine the current config serial by following the helper_config/latest symlink.

        Expected structure:
          $OMD_ROOT/var/check_mk/core/helper_config/
            <serial_id>/                # directories named by a serial
            latest -> <serial_id>/      # symlink pointing to the active serial directory

        The serial is taken from the basename of the resolved target of 'latest'.
        Errors (symlink missing/not a symlink, invalid target) raise GetConfigSerialError.
        """

        config = get_config()
        latest_link = config.helper_config_dir / "latest"

        if not latest_link.exists():
            logger.exception("Latest symlink %s does not exist", latest_link)
            raise GetConfigSerialError("latest symlink missing")

        if not latest_link.is_symlink():
            logger.exception("Path %s exists but is not a symlink", latest_link)
            raise GetConfigSerialError("latest is not a symlink")

        try:
            # Resolve the symlink; we only need the final directory name.
            target_path = latest_link.resolve(strict=True)
        except FileNotFoundError:
            logger.exception("Symlink %s points to a non-existent target", latest_link)
            raise GetConfigSerialError("latest symlink target missing")
        except OSError as e:
            logger.exception("Failed to resolve symlink %s: %s", latest_link, e)
            raise GetConfigSerialError("could not resolve latest symlink")

        serial = target_path.name
        return serial
