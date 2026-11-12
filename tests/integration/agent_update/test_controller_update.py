#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The agent controller's update cycle against the agent receiver, with Wiremock as the site.

The test runs the built controller against the receiver. It fails when the two disagree on a
path, a JSON field or the client certificate.
"""

import base64
import json
import os
import shutil
import subprocess
from http import HTTPMethod, HTTPStatus
from pathlib import Path
from uuid import UUID, uuid4

from cmk.agent_receiver.lib.certs import sign_csr
from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.testlib.agent_receiver.builder import AgentReceiverSite
from cmk.testlib.agent_receiver.certs import generate_csr_pair
from cmk.testlib.agent_receiver.runner import AgentReceiverRunner
from cmk.testlib.agent_receiver.wiremock import Request, Response, Wiremock, WMapping

HOST_NAME = "my-host"
INSTALLED_HASH = "0123456789abcdef"
OFFERED_HASH = "fedcba9876543210"
PACKAGE = b"\x00\xff\r\n binary package bytes \x1f\x8b"


def _site_path(site: AgentReceiverSite, action: str) -> str:
    """The endpoint of the site's internal REST API that the receiver forwards an update request
    to, see deployment_status() and deployment_download() in
    packages/cmk-agent-receiver/cmk/agent_receiver/agent_receiver/checkmk_rest_api.py."""
    return (
        f"/{site.config.site_name}/check_mk/api/internal"
        f"/objects/agent_deployment_internal/{HOST_NAME}/actions/{action}/invoke"
    )


def _site_answers(wiremock: Wiremock, site: AgentReceiverSite, action: str, body: bytes) -> None:
    """Configure Wiremock to answer `body` to each request that the receiver forwards to the
    site for `action`."""
    wiremock.setup_mapping(
        WMapping(
            request=Request(method="POST", url=_site_path(site, action)),
            response=Response(status=HTTPStatus.OK, base64Body=base64.b64encode(body).decode()),
        )
    )


def _registered_uuid(site: AgentReceiverSite) -> UUID:
    # A registration leaves a symlink named after the UUID, pointing at the host's directory.
    # The update endpoints take the host name from that link and refuse an unregistered UUID.
    uuid = uuid4()
    agent_output_dir = site.config.agent_output_dir
    agent_output_dir.mkdir(parents=True)
    (agent_output_dir / str(uuid)).symlink_to(agent_output_dir / HOST_NAME)
    return uuid


def _install_controller(
    runner: AgentReceiverRunner, uuid: UUID, install_dir: Path, cert_log: Path
) -> Path:
    """Set up the controller in a single-directory deployment, registered to the runner.

    The controller detects that deployment from the location of its own executable. The test
    user owns runtime/controller. The controller switches to that owner, so it stays the test
    user. The files stand in for `cmk-agent-ctl register`: a registration would need many more
    answers from the site, and `import` creates a connection that cannot be an update source.
    """
    site = runner.site
    for sub_dir in ["package/bin", "package/config", "package/agent", "runtime/controller"]:
        (install_dir / sub_dir).mkdir(parents=True)
    # Copied, not linked: the controller resolves links and would end up outside the deployment.
    controller = Path(shutil.copy(os.environ["CMK_AGENT_CTL"], install_dir / "package/bin"))
    # The controller recognizes the deployment by this file, even when it is empty.
    (install_dir / "package/config/cmk-agent-ctl.toml").write_text("")
    # The file turns the updater on. Without installer_socket, the package stays in the spool.
    (install_dir / "package/config/cmk-agent-ctl-update.toml").write_text("")
    # The installed package, which the controller reports in its status request.
    (install_dir / "package/agent/agent_info.json").write_text(
        json.dumps({"hash": INSTALLED_HASH, "platform": "linux_deb"})
    )

    agent_ca = CertificateWithPrivateKey.load_combined_file_content(
        site.config.agent_ca_path.read_text(), passphrase=None
    )
    site_ca = CertificateWithPrivateKey.load_combined_file_content(
        site.config.site_ca_path.read_text(), passphrase=None
    )
    # The receiver accepts only a client certificate from its agent CA, and only for the UUID
    # in the URL.
    private_key, csr = generate_csr_pair(cn=str(uuid))
    certificate = sign_csr(csr, lifetime_in_months=12, keypair=agent_ca, cert_log=cert_log)
    # A connection as `cmk-agent-ctl register` saves it. The controller checks the receiver's
    # certificate against root_certs, and for the certificate's CN, which is the site name.
    connection = {
        "uuid": str(uuid),
        "private_key": private_key.dump_pem(None).str,
        "certificate": certificate.dump_pem().str,
        "root_certs": [site_ca.certificate.dump_pem().str],
        "receiver_port": runner.port,
    }
    runtime_dir = install_dir / "runtime/controller"
    (runtime_dir / "registered_connections.json").write_text(
        json.dumps({"pull": {f"127.0.0.1/{site.config.site_name}": connection}})
    )
    # The update source, as the registration records it.
    (runtime_dir / "agent-update-state.json").write_text(
        json.dumps({"source": {"uuid": str(uuid), "available": True}})
    )
    return controller


def test_update_cycle_downloads_the_package_the_site_offers(
    ar_runner: AgentReceiverRunner, wiremock: Wiremock, tmp_path: Path
) -> None:
    # A host registered to the receiver, whose site offers one package: the status request
    # learns of the package, and the download request fetches it.
    site = ar_runner.site
    uuid = _registered_uuid(site)
    controller = _install_controller(
        ar_runner, uuid, tmp_path / "controller", tmp_path / "issued.jsonl"
    )
    offer = {"target_agent": {"aghash": OFFERED_HASH, "signatures": []}}
    _site_answers(wiremock, site, "status", json.dumps(offer).encode())
    _site_answers(wiremock, site, "download", PACKAGE)

    # The offer carries no signature. Without an installer socket, the controller leaves the
    # spooled package where it is, and the cycle ends there.
    cycle = subprocess.run(
        [controller, "-vv", "update", "--skip-signatures"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert cycle.returncode == 0, cycle
    forwarded = [
        json.loads(request.body)
        for action in ["status", "download"]
        for request in wiremock.get_all_url_path_requests(_site_path(site, action), HTTPMethod.POST)
    ]
    # The receiver adds the UUID before it forwards a request to the site.
    assert forwarded == [
        {"platform": "linux_deb", "installed_aghash": INSTALLED_HASH, "uuid": str(uuid)},
        {"platform": "linux_deb", "aghash": OFFERED_HASH, "uuid": str(uuid)},
    ]
    spooled = tmp_path / "controller/runtime/controller/update" / f"{OFFERED_HASH}.deb"
    assert spooled.read_bytes() == PACKAGE
