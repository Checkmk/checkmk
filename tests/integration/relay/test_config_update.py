#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_receiver.certs import serialize_to_pem
from cmk.relay_protocols.tasks import RelayConfigTask
from tests.testlib.site import Site

from ..agent_receiver.test_agent_receiver import generate_csr_pair

pytestmark = pytest.mark.skip_if_not_edition("cloud", "managed")


@pytest.skip(
    "Not all parts are integrated yet. This will only cause test failures", allow_module_level=True
)
class TestRelay:
    registered_relays: set[str] = set()
    created_hosts: set[str] = set()
    _site: Site | None = None

    def _register_relay(self, alias: str) -> str:
        assert self._site is not None

        _, csr = generate_csr_pair(alias)
        relay_id = self._site.openapi_agent_receiver.relays.register(
            alias=alias, csr=serialize_to_pem(csr)
        )
        self.registered_relays.add(relay_id)
        return relay_id

    def teardown_method(self, method: object) -> None:
        if self._site is None:
            return

        for relay_id in self.registered_relays:
            _, etag = self._site.openapi.relays.get(relay_id)
            self._site.openapi.relays.delete(relay_id, etag)

        self.registered_relays.clear()

        if self.created_hosts:
            self._site.openapi.hosts.bulk_delete(list(self.created_hosts))
            self._site.openapi.changes.activate_and_wait_for_completion()
            self.created_hosts.clear()

    def test_config_update(self, site: Site) -> None:
        """
        Test that unrelated config change triggers submission of the new activated config to relays
        """
        self._site = site
        alias = "foo_alias"
        relay_id = self._register_relay(alias=alias)

        hostname = "localhost"
        site.openapi.hosts.create(hostname=hostname, attributes={"ipaddress": "127.0.0.1"})
        self.created_hosts.add(hostname)

        site.openapi.changes.activate_and_wait_for_completion()

        tasks = site.openapi_agent_receiver.relays.get_tasks(relay_id)
        assert len(tasks) == 1
        assert isinstance(tasks[0].spec, RelayConfigTask)
