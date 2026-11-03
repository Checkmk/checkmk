#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
import zlib
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import httpx2
import pytest

from cmk.agent_receiver.lib.certs import serialize_to_pem, sign_csr
from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.testlib.agent_receiver.builder import AgentReceiverSite
from cmk.testlib.agent_receiver.certs import generate_csr_pair
from cmk.testlib.agent_receiver.runner import AgentReceiverRunner
from cmk.testlib.agent_receiver.wiremock import Request, Response, Wiremock, WMapping

type _SiteMethod = Literal["GET", "PUT"]

PUSH_HOST = "push-host"
NEW_HOST = "new-host"

# Long enough that a push queued behind the registration clearly ends after it.
SITE_DELAY_SECONDS = 5.0
# Long enough for the registration to be waiting for the site.
REGISTRATION_HEAD_START_SECONDS = 1.0


@pytest.fixture
def ar_runner(ar_site: AgentReceiverSite) -> Iterator[AgentReceiverRunner]:
    runner = AgentReceiverRunner(ar_site)
    with runner.running():
        runner.wait_for_running()
        yield runner


def _site_answers(
    wiremock: Wiremock, method: _SiteMethod, url: str, body: object, delay_seconds: float = 0.0
) -> None:
    wiremock.setup_mapping(
        WMapping(
            request=Request(method=method, url=url),
            response=Response(
                status=HTTPStatus.OK,
                body=json.dumps(body),
                headers={"Content-Type": "application/json"},
                fixedDelayMilliseconds=int(delay_seconds * 1000),
            ),
        )
    )


def _api_path(site: AgentReceiverSite, endpoint: str) -> str:
    return f"/{site.config.site_name}/check_mk/api/1.0/{endpoint}"


def _push_host(site: AgentReceiverSite) -> UUID:
    uuid = uuid4()
    agent_output_dir = site.config.agent_output_dir
    agent_output_dir.mkdir(parents=True)
    (agent_output_dir / str(uuid)).symlink_to(site.config.omd_root / "tmp/push-agent" / PUSH_HOST)
    return uuid


def _agent_cert(site: AgentReceiverSite, uuid: UUID, cert_log: Path) -> CertificateWithPrivateKey:
    private_key, csr = generate_csr_pair(cn=str(uuid))
    ca = CertificateWithPrivateKey.load_combined_file_content(
        site.config.agent_ca_path.read_text(), passphrase=None
    )
    certificate = sign_csr(csr, lifetime_in_months=12, keypair=ca, cert_log=cert_log)
    return CertificateWithPrivateKey(certificate=certificate, private_key=private_key)


def _register_existing(runner: AgentReceiverRunner) -> httpx2.Response:
    uuid = uuid4()
    _key, csr = generate_csr_pair(cn=str(uuid))
    with runner.http_client() as client:
        return client.post(
            f"/{runner.site.config.site_name}/agent-receiver/register_existing",
            auth=("automation", "secret"),
            json={"uuid": str(uuid), "csr": serialize_to_pem(csr), "host_name": NEW_HOST},
            timeout=SITE_DELAY_SECONDS * 3,
        )


def _register_new(runner: AgentReceiverRunner) -> httpx2.Response:
    uuid = uuid4()
    _key, csr = generate_csr_pair(cn=str(uuid))
    with runner.http_client() as client:
        return client.post(
            f"/{runner.site.config.site_name}/agent-receiver/register_new",
            auth=("automation", "secret"),
            json={"uuid": str(uuid), "csr": serialize_to_pem(csr), "agent_labels": {}},
            timeout=SITE_DELAY_SECONDS * 3,
        )


@pytest.mark.parametrize(
    "slow_endpoint, registration",
    [
        pytest.param(
            ("PUT", f"objects/host_config_internal/{NEW_HOST}/actions/register/invoke"),
            _register_existing,
            id="register_existing",
        ),
        pytest.param(("GET", "version"), _register_new, id="register_new"),
    ],
)
def test_agent_data_is_saved_while_a_registration_waits_for_the_site(
    ar_runner: AgentReceiverRunner,
    wiremock: Wiremock,
    tmp_path: Path,
    slow_endpoint: tuple[_SiteMethod, str],
    registration: Callable[[AgentReceiverRunner], httpx2.Response],
) -> None:
    site = ar_runner.site
    site_answers: dict[tuple[_SiteMethod, str], object] = {
        ("GET", "agent_controller_certificates_settings"): {"lifetime_in_months": 12},
        ("GET", "version"): {"edition": "ultimate"},
        ("PUT", f"objects/host_config_internal/{NEW_HOST}/actions/register/invoke"): {
            "connection_mode": "push-agent"
        },
    }
    for (method, endpoint), body in site_answers.items():
        _site_answers(
            wiremock,
            method,
            _api_path(site, endpoint),
            body,
            delay_seconds=SITE_DELAY_SECONDS if (method, endpoint) == slow_endpoint else 0.0,
        )
    uuid = _push_host(site)
    agent_cert = _agent_cert(site, uuid, tmp_path / "issued.jsonl")

    with ThreadPoolExecutor(max_workers=1) as executor:
        pending_registration = executor.submit(registration, ar_runner)
        time.sleep(REGISTRATION_HEAD_START_SECONDS)

        with ar_runner.mtls_client(agent_cert) as client:
            push = client.post(
                f"/{site.config.site_name}/agent-receiver/agent_data/{uuid}",
                headers={"compression": "zlib"},
                files={"monitoring_data": zlib.compress(b"<<<check_mk>>>\n")},
                timeout=SITE_DELAY_SECONDS * 3,
            )
        registration_was_pending = not pending_registration.done()
        registration_response = pending_registration.result()

    assert push.status_code == HTTPStatus.NO_CONTENT, push.text
    assert registration_was_pending
    assert registration_response.status_code == HTTPStatus.OK, registration_response.text
