#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, UTC
from typing import override
from urllib.parse import urlsplit

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import get_agent_receiver_port, SiteId
from cmk.ccc.user import UserId
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.gui.config import active_config, Config
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.site_config import site_is_local
from cmk.gui.token_auth import AgentRegistrationToken, AuthToken, get_token_store, TokenStore
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    remote_automation_config_from_site_config,
)
from cmk.licensing.basics.options import OptionName
from cmk.licensing.registry import is_option_enabled
from cmk.livestatus_client import SiteConfiguration
from cmk.utils import paths
from cmk.utils.agent_registration import HostAgentConnectionMode


class PushRegistration(BaseModel):
    port: int = Field(ge=1, le=65535)
    registration_token: str = Field(repr=False)
    site_ca_certificate: str = Field(repr=False)


def local_push_registration(
    host_name: HostName, issuer: UserId, *, push_supported: bool
) -> PushRegistration:
    """Prepare credentials using the receiving site's agent-registration capability."""
    if not push_supported:
        raise ValueError(
            _("The selected monitoring site does not support push mode. Use pull mode instead.")
        )
    ca_pem = paths.root_cert_file.read_bytes()
    if not ca_pem.strip():
        raise ValueError("The site CA certificate is empty")
    # ca.pem also contains the private CA key. Export only the parsed certificate.
    site_ca = Certificate.load_pem(CertificatePEM(ca_pem))
    port = get_agent_receiver_port(paths.omd_root)
    token = issue_push_token(
        host_name=host_name, issuer=issuer, token_store=get_token_store(), now=datetime.now(UTC)
    )
    return PushRegistration(
        port=port,
        registration_token=f"0:{token.token_id}",
        site_ca_certificate=site_ca.dump_pem().bytes.decode("utf-8"),
    )


class AutomationKubernetesPushRegistration(AutomationCommand[tuple[HostName, UserId]]):
    """Site-authenticated automation; the central caller must authorize the new host first."""

    @override
    def command_name(self) -> str:
        return "kubernetes-push-registration"

    @override
    def get_request(self, config: Config, request: Request) -> tuple[HostName, UserId]:
        return (
            request.get_validated_type_input_mandatory(HostName, "host_name"),
            request.get_validated_type_input_mandatory(UserId, "issuer"),
        )

    @override
    def execute(self, api_request: tuple[HostName, UserId]) -> dict[str, object]:
        return local_push_registration(
            *api_request,
            push_supported=is_option_enabled(paths.omd_root, OptionName.AGENT_REGISTRATION),
        ).model_dump(mode="json")


def request_push_registration(
    site_config: SiteConfiguration, host_name: HostName, issuer: UserId
) -> PushRegistration:
    """Issue on the redeeming site, after the central caller has checked host permissions."""
    if site_is_local(site_config):
        return local_push_registration(
            host_name,
            issuer,
            push_supported=is_option_enabled(paths.omd_root, OptionName.AGENT_REGISTRATION),
        )
    return PushRegistration.model_validate(
        do_remote_automation(
            automation_config=remote_automation_config_from_site_config(site_config),
            command="kubernetes-push-registration",
            vars_=[("host_name", host_name), ("issuer", issuer)],
            debug=active_config.debug,
        )
    )


def issue_push_token(
    *, host_name: HostName, issuer: UserId, token_store: TokenStore, now: datetime
) -> AuthToken:
    """Called only by the push deployment action, on the selected monitoring site."""
    return token_store.issue(
        AgentRegistrationToken(
            host_name=host_name,
            connection_mode=HostAgentConnectionMode.PUSH,
            comment="Kubernetes Quick Setup",
        ),
        issuer=issuer,
        now=now,
        valid_for=relativedelta(hours=1),
    )


def push_receiver_url(
    *,
    site_id: SiteId,
    site_url: str,
    browser_host: str,
    port: int,
    override_host: str | None = None,
) -> str:
    """Use the selected site's URL hostname, falling back to the browser's hostname."""
    host = override_host or urlsplit(site_url).hostname or browser_host
    if not host:
        raise ValueError("Cannot determine the push receiver hostname")
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"https://{host}:{port}/{site_id}"
