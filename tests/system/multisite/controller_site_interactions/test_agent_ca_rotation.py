#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import json
import urllib.parse
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pytest
import requests

from cmk.ccc.hostaddress import HostName
from cmk.crypto.certificate import (
    Certificate,
    CertificatePEM,
    CertificateSigningRequest,
    CertificateWithPrivateKey,
)
from cmk.crypto.keys import PrivateKey
from cmk.crypto.x509 import X509Name
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import run
from tests.testlib.system.agent import (
    clean_up_host,
    controller_connection_json,
    controller_status_json,
    register_controller,
)
from tests.testlib.system.site import Site

pytestmark = pytest.mark.skip_if_faked_artifacts

_AGENT_CA_PATH = Path("etc/ssl/agents/ca.pem")
_CONTROLLER_REGISTRY_PATH = Path("/var/lib/cmk-agent/registered_connections.json")


def _generate_csr_pair(cn: str) -> tuple[PrivateKey, CertificateSigningRequest]:
    private_key = PrivateKey.generate_rsa(2048)
    return (
        private_key,
        CertificateSigningRequest.create(
            subject_name=X509Name.create(common_name=cn),
            subject_private_key=private_key,
        ),
    )


def _agent_receiver_url(site: Site, endpoint: str) -> str:
    return urllib.parse.urljoin(site.openapi_agent_receiver.base_url, endpoint)


@dataclass(frozen=True)
class _AgentCtl:
    site: Site
    path: Path

    @classmethod
    def register(cls, site: Site, path: Path, hostname: HostName) -> Self:
        register_controller(path, site, hostname)
        return cls(site, path)

    @property
    def uuid_(self) -> str:
        uuid_: str = controller_connection_json(controller_status_json(self.path), self.site)[
            "uuid"
        ]
        return uuid_

    @property
    def certificate(self) -> Certificate:
        registry = json.loads(run(["cat", _CONTROLLER_REGISTRY_PATH.as_posix()], sudo=True).stdout)
        (connection,) = (c for c in registry["pull"].values() if c["uuid"] == self.uuid_)
        return Certificate.load_pem(CertificatePEM(connection["certificate"]))

    def renew_certificate(self) -> None:
        run([self.path.as_posix(), "renew-certificate", self.uuid_], sudo=True)

    def is_accepted(self) -> bool:
        try:
            controller_connection_json(controller_status_json(self.path), self.site)
        except AssertionError:
            return False
        return True


@dataclass(frozen=True)
class _SimulatedAgent:
    """An agent talking to the agent receiver directly, standing in for another controller."""

    site: Site
    uuid_: str
    cert_path: Path
    key_path: Path

    @classmethod
    def register(cls, site: Site, hostname: HostName, tmp_path: Path) -> Self:
        uuid_ = str(uuid.uuid4())
        private_key, csr = _generate_csr_pair(uuid_)
        response = site.openapi_agent_receiver.post(
            _agent_receiver_url(site, "register_existing"),
            auth=("cmkadmin", site.admin_password),
            json={"uuid": uuid_, "csr": csr.dump_pem().str, "host_name": hostname},
        )
        response.raise_for_status()

        agent = cls(site, uuid_, tmp_path / f"{uuid_}.pem", tmp_path / f"{uuid_}.key")
        agent._store_credentials(response.json()["agent_cert"], private_key)
        return agent

    @property
    def certificate(self) -> Certificate:
        return Certificate.load_pem(CertificatePEM(self.cert_path.read_text()))

    def renew_certificate(self) -> None:
        private_key, csr = _generate_csr_pair(self.uuid_)
        response = self.site.openapi_agent_receiver.post(
            _agent_receiver_url(self.site, f"renew_certificate/{self.uuid_}"),
            json={"csr": csr.dump_pem().str},
            cert=self._cert_tuple(),
        )
        response.raise_for_status()
        self._store_credentials(response.json()["agent_cert"], private_key)

    def is_accepted(self) -> bool:
        try:
            response = self.site.openapi_agent_receiver.get(
                _agent_receiver_url(self.site, f"registration_status_v2/{self.uuid_}"),
                cert=self._cert_tuple(),
            )
        except requests.exceptions.ConnectionError:
            return False
        return response.ok and response.json()["status"] == "Registered"

    def _cert_tuple(self) -> tuple[str, str]:
        return str(self.cert_path), str(self.key_path)

    def _store_credentials(self, agent_cert: str, private_key: PrivateKey) -> None:
        self.cert_path.write_text(agent_cert)
        self.key_path.write_bytes(private_key.dump_pem(None).bytes)


def _agent_ca(site: Site) -> Certificate:
    return CertificateWithPrivateKey.load_combined_file_content(
        site.read_file(_AGENT_CA_PATH), passphrase=None
    ).certificate


def _wait_for_agent_receiver(site: Site) -> None:
    def _is_up() -> bool:
        try:
            site.openapi_agent_receiver.get(
                _agent_receiver_url(site, f"registration_status_v2/{uuid.uuid4()}")
            )
        except requests.exceptions.ConnectionError:
            return False
        return True

    wait_until(_is_up, timeout=30, interval=0.5, condition_name="agent receiver is up")


def _remove_retired_agent_cas(site: Site) -> None:
    retired_cas = [
        name
        for name in site.listdir(_AGENT_CA_PATH.parent)
        if name.endswith(".pem") and name != _AGENT_CA_PATH.name
    ]
    if not retired_cas:
        return
    for name in retired_cas:
        site.delete_file(_AGENT_CA_PATH.parent / name)
    site.omd("reload", "agent-receiver", check=True)
    _wait_for_agent_receiver(site)


@contextlib.contextmanager
def _clean_up_retired_agent_cas(site: Site) -> Iterator[None]:
    try:
        yield
    finally:
        _remove_retired_agent_cas(site)


@pytest.mark.skip_if_not_containerized
def test_agent_ca_rotation(central_site: Site, agent_ctl: Path, tmp_path: Path) -> None:
    """Agents keep working until they renew, after dropping the retired CA only renewed ones do."""
    controller_host = HostName("ca-rotation-controller")
    renewing_host = HostName("ca-rotation-renewing")
    stale_host = HostName("ca-rotation-stale")

    with (
        clean_up_host(central_site, controller_host),
        clean_up_host(central_site, renewing_host),
        clean_up_host(central_site, stale_host),
        _clean_up_retired_agent_cas(central_site),
    ):
        for hostname in (controller_host, renewing_host, stale_host):
            central_site.openapi.hosts.create(
                hostname=hostname, attributes={"ipaddress": "127.0.0.1"}
            )
        central_site.openapi.changes.activate_and_wait_for_completion()

        controller = _AgentCtl.register(central_site, agent_ctl, controller_host)
        renewing_agent = _SimulatedAgent.register(central_site, renewing_host, tmp_path)
        stale_agent = _SimulatedAgent.register(central_site, stale_host, tmp_path)
        old_ca = _agent_ca(central_site)

        central_site.check_output(["cmk-cert", "rotate", "agent-ca"])
        _wait_for_agent_receiver(central_site)

        new_ca = _agent_ca(central_site)
        assert new_ca.show_fingerprint() != old_ca.show_fingerprint(), "Agent CA was not replaced"
        assert controller.is_accepted(), "Controller rejected before renewal"
        assert renewing_agent.is_accepted(), "Agent rejected before renewal"
        assert stale_agent.is_accepted(), "Agent rejected before renewal"

        controller.renew_certificate()
        renewing_agent.renew_certificate()

        controller.certificate.verify_is_signed_by(new_ca)
        renewing_agent.certificate.verify_is_signed_by(new_ca)

        _remove_retired_agent_cas(central_site)

        assert controller.is_accepted(), "Controller rejected after renewal"
        assert renewing_agent.is_accepted(), "Agent rejected after renewal"
        assert not stale_agent.is_accepted(), "Agent with certificate of removed CA still accepted"
