#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

from fastapi.testclient import TestClient

from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.relay_protocols.tasks import CertRotationTask
from cmk.testlib.agent_receiver.clients import RelayClient, SiteClient
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_a_relay_receives_the_additional_ca_of_a_cert_rotation_task(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))
    task = CertRotationTask(
        additional_ca_cert=CertificateWithPrivateKey.generate_self_signed(
            common_name="Site 'heute' local CA",
            organization="Checkmk Site heute",
            key_size=1024,
            is_ca=True,
        )
        .certificate.dump_pem()
        .str
    )

    SiteClient(test_client, site.site_name).create_task(relay_id, task)

    [stored] = relay.get_task_list().tasks
    assert stored.spec == task
