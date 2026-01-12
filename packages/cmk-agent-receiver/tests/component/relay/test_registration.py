#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from datetime import datetime, timedelta, UTC
from http import HTTPStatus

from dateutil.relativedelta import relativedelta

from cmk.agent_receiver.lib.config import Config
from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver import certs as certslib
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock
from cmk.testlib.agent_receiver.tasks import get_relay_tasks, push_task


def test_a_relay_can_be_registered(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify that a relay can be registered with the agent receiver and tasks can be retrieved for it.

    Test steps:
    1. Register a relay with the agent receiver
    2. Create a config folder for the relay
    3. Verify that tasks can be retrieved for the registered relay
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    resp = agent_receiver.register_relay(relay_id, "relay1")
    assert resp.status_code == HTTPStatus.OK

    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    resp = agent_receiver.get_relay_tasks(relay_id)
    assert resp.status_code == HTTPStatus.OK


def test_registering_a_relay_does_not_affect_other_relays(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that registering a new relay does not affect tasks belonging to other already registered relays.

    Test steps:
    1. Register first relay and push a task to it
    2. Register second relay
    3. Verify first relay's task remains unaffected
    """
    relay_1_id = random_relay_id()
    relay_2_id = random_relay_id()
    site.set_scenario([], [(relay_1_id, OP.ADD), (relay_2_id, OP.ADD)])
    register_relay(agent_receiver, "relay1", relay_1_id)
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_1_id])
    agent_receiver.set_serial(cf.serial)

    push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_1_id,
        spec=FetchAdHocTask(payload=".."),
        site_cn=site_name,
    )

    register_relay(agent_receiver, "relay2", relay_2_id)
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_1_id, relay_2_id])
    agent_receiver.set_serial(cf.serial)

    tasks_A = get_relay_tasks(agent_receiver, relay_1_id)
    assert len(tasks_A.tasks) == 1


def test_certificate_validity_period(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that the certificate returned by the registration endpoint has the desired
    validity period.

    Test steps:
    1. Register a relay with the agent receiver
    2. Check the validity of the returned certificate
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    resp = agent_receiver.register_relay(relay_id, "relay1")
    assert resp.status_code == HTTPStatus.OK

    # Verify that the certificate has correct validity period bounds.
    now = datetime.now(tz=UTC)
    cert = certslib.read_certificate(resp.json()["client_cert"])
    assert cert.not_valid_before_utc <= now
    assert cert.not_valid_before_utc >= now - timedelta(minutes=1)
    assert cert.not_valid_after_utc <= now + relativedelta(months=3)
