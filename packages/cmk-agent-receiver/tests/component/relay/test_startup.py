#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.main import main_app
from cmk.agent_receiver.relay.lib.shared_types import Serial
from cmk.relay_protocols.tasks import RelayConfigTask, TaskListResponse, TaskResponse, TaskStatus
from cmk.testlib.agent_receiver.clients import RelayClient
from cmk.testlib.agent_receiver.relay_config_generator import RelayConfig
from cmk.testlib.agent_receiver.site_mock import SiteMock

# In order to test the lifespan function, we have to use TestClient with "with":
# https://fastapi.tiangolo.com/advanced/testing-events/


@pytest.mark.parametrize("edition", ["ultimatemt", "ultimate", "cloud"])
def test_startup_with_relays(site: SiteMock, site_context: Config, edition: str) -> None:
    """Verify that starting the agent receiver application with a supported edition creates relay config tasks for all configured relays.

    Test steps:
    1. Configure supported edition and relay folders
    2. Start the application
    3. Verify relay config tasks are created
    """
    relays = [str(uuid.uuid4()), str(uuid.uuid4())]

    _create_version_folder(site_context.omd_root, edition)
    site.set_scenario(relays)
    relay_config = site.push_config(relays)

    tasks = _do_test_and_get_tasks(relays[0], relay_config.serial, site_context)

    assert len(tasks) == 1
    task = tasks[0]
    assert task.status == TaskStatus.PENDING
    assert isinstance(task.spec, RelayConfigTask)


@pytest.mark.parametrize("edition", ["ultimatemt", "ultimate", "cloud"])
def test_no_relays_folder(site: SiteMock, site_context: Config, edition: str) -> None:
    """Verify that starting the application does not create relay config tasks when the relays folder is missing.

    Test steps:
    1. Configure supported edition but remove relays folder
    2. Start the application
    3. Verify no relay config tasks are created
    """
    relays = [str(uuid.uuid4()), str(uuid.uuid4())]

    site.set_scenario(relays)
    relay_config = site.push_config(relays)
    shutil.rmtree(site_context.helper_config_dir / "latest/relays")
    _create_version_folder(site_context.omd_root, edition)

    tasks = _do_test_and_get_tasks(relays[0], relay_config.serial, site_context)

    assert len(tasks) == 0


@pytest.mark.parametrize("edition", ["ultimatemt", "ultimate", "cloud"])
def test_empty_relays_folder(site: SiteMock, site_context: Config, edition: str) -> None:
    """Verify that starting the application does not create relay config tasks when the relays folder exists but is empty.

    Test steps:
    1. Configure supported edition with empty relays folder
    2. Start the application
    3. Verify no relay config tasks are created
    """
    relays = [str(uuid.uuid4()), str(uuid.uuid4())]

    site.set_scenario(relays)
    relay_config = site.push_config(relays)
    for rid in relays:
        shutil.rmtree(site_context.helper_config_dir / f"latest/relays/{rid}")

    _create_version_folder(site_context.omd_root, edition)

    tasks = _do_test_and_get_tasks(relays[0], relay_config.serial, site_context)

    assert len(tasks) == 0


@pytest.mark.parametrize("edition", ["community", "pro"])
def test_unsupported_editions(site: SiteMock, site_context: Config, edition: str) -> None:
    """Verify that starting the application with an unsupported edition does not create relay config tasks.

    Test steps:
    1. Configure unsupported edition with relays
    2. Start the application
    3. Verify no relay config tasks are created
    """
    relays = [str(uuid.uuid4()), str(uuid.uuid4())]

    site.set_scenario(relays)
    relay_config = site.push_config(relays)
    _create_version_folder(site_context.omd_root, edition)

    tasks = _do_test_and_get_tasks(relays[0], relay_config.serial, site_context)

    assert len(tasks) == 0


def _do_test_and_get_tasks(
    relay_id: str, serial: Serial, site_context: Config
) -> list[TaskResponse]:
    app = main_app()
    with TestClient(app) as client:
        relay = RelayClient(client, site_context.site_name, relay_id)
        relay.apply_config(RelayConfig(serial=serial, files={}))
        tasks_resp = relay.get_tasks()
        return TaskListResponse.model_validate(tasks_resp.json()).tasks


def _create_version_folder(omd_root: Path, edition: str) -> None:
    version_path = omd_root / f"some.detailed.version.{edition}"
    version_path.mkdir(exist_ok=True)
    version_link = omd_root / "version"
    if version_link.exists() or version_link.is_symlink():
        version_link.unlink()
    version_link.symlink_to(version_path)
