#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override
from uuid import UUID

from pydantic import ValidationError

import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.log import logger
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
)
from cmk.utils.agent_registration import get_r4r_filepath, UUIDLinkManager, UUIDRegistration
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.security_event import log_security_event, SecurityEvent


def remove_tls_registration(
    hosts_by_site: Sequence[
        tuple[LocalAutomationConfig | RemoteAutomationConfig, Sequence[HostName]]
    ],
    *,
    debug: bool,
) -> None:
    for automation_config, host_names in hosts_by_site:
        if not host_names:
            continue

        if isinstance(automation_config, LocalAutomationConfig):
            _remove_tls_registration(host_names)
            continue

        do_remote_automation(
            automation_config,
            "remove-tls-registration",
            [("host_names", json.dumps(host_names))],
            debug=debug,
        )


class AutomationRemoveTLSRegistration(AutomationCommand[Sequence[HostName]]):
    @override
    def command_name(self) -> str:
        return "remove-tls-registration"

    @override
    def get_request(self, config: Config, request: Request) -> Sequence[HostName]:
        value = json.loads(request.get_ascii_input_mandatory("host_names", "[]"))
        if not isinstance(value, list):
            raise MKGeneralException(f"Not a list of host names: {value}")
        valid_hostnames, invalid_hostnames = [], []
        for hostname in value:
            try:
                valid_hostnames.append(HostName(hostname))
            except ValueError:
                invalid_hostnames.append(hostname)
        if invalid_hostnames:
            logger.warning(
                "remove-tls-registration called with the following invalid host names: %(host_names)s",
                {"host_names": ", ".join(invalid_hostnames)},
            )
        return valid_hostnames

    @override
    def execute(self, api_request: Sequence[HostName]) -> None:
        _remove_tls_registration(api_request)


class UUIDAlreadyLinkedError(MKGeneralException):
    pass


class UUIDOfOpenRequestError(MKGeneralException):
    pass


@dataclass
class LinkedUUIDRefusedEvent(SecurityEvent):
    def __init__(
        self, *, host_name: HostName | None, uuid: UUID, linked_host_name: HostName
    ) -> None:
        super().__init__(
            "registration of a linked UUID refused",
            {
                "host_name": None if host_name is None else str(host_name),
                "uuid": str(uuid),
                "linked_host_name": str(linked_host_name),
            },
            SecurityEvent.Domain.auth,
        )


@dataclass
class UUIDOfOpenRequestRefusedEvent(SecurityEvent):
    def __init__(self, *, host_name: HostName, uuid: UUID) -> None:
        super().__init__(
            "registration of a UUID with an open request refused",
            {"host_name": str(host_name), "uuid": str(uuid)},
            SecurityEvent.Domain.auth,
        )


def link_uuid_of_existing_host(
    host_name: HostName, uuid: UUID, *, push_configured: bool, registration: UUIDRegistration
) -> None:
    """Called by the REST endpoints of the registration of an existing host. The REST framework
    holds the configuration lock of the site while the checks read the UUID links of the site and
    the requests in requests-for-registration/NEW and PENDING."""
    verify_uuid_is_not_linked(uuid, host_name=host_name)
    if any(
        get_r4r_filepath(request_dir, uuid).exists()
        for request_dir in (cmk.utils.paths.r4r_new_dir, cmk.utils.paths.r4r_pending_dir)
    ):
        log_security_event(UUIDOfOpenRequestRefusedEvent(host_name=host_name, uuid=uuid))
        raise UUIDOfOpenRequestError(
            f"The UUID {uuid} belongs to an open request of the automatic registration."
        )
    link_uuid_of_registration(
        host_name, uuid, push_configured=push_configured, registration=registration
    )


def link_uuid_of_registration(
    host_name: HostName, uuid: UUID, *, push_configured: bool, registration: UUIDRegistration
) -> None:
    _uuid_link_manager().link_registration(
        host_name, uuid, push_configured=push_configured, registration=registration
    )


def verify_uuid_is_not_linked(uuid: UUID, *, host_name: HostName | None) -> None:
    if (linked_host_name := _uuid_link_manager().linked_host_name(uuid)) is not None:
        log_security_event(
            LinkedUUIDRefusedEvent(
                host_name=host_name, uuid=uuid, linked_host_name=linked_host_name
            )
        )
        raise UUIDAlreadyLinkedError(f"The UUID {uuid} is already linked to a host.")


def agent_updates_permitted(host_name: HostName, uuid: UUID) -> bool:
    """Whether the registration that linked the UUID to the host permits agent updates"""
    uuid_link_manager = _uuid_link_manager()
    if uuid_link_manager.linked_host_name(uuid) != host_name:
        return False
    try:
        registration = uuid_link_manager.registration(uuid)
    except ValidationError as e:
        logger.warning(
            "The registration file of UUID %(uuid)s is unreadable: %(error)s",
            {"uuid": uuid, "error": e},
        )
        return False
    return registration is not None and registration.agent_updates_permitted is True


def _uuid_link_manager() -> UUIDLinkManager:
    return UUIDLinkManager(
        received_outputs_dir=cmk.utils.paths.received_outputs_dir,
        data_source_dir=cmk.utils.paths.data_source_push_agent_dir,
        r4r_discoverable_dir=cmk.utils.paths.r4r_discoverable_dir,
        uuid_lookup_dir=cmk.utils.paths.uuid_lookup_dir,
        registrations_dir=cmk.utils.paths.registrations_dir,
    )


def _remove_tls_registration(host_names: Sequence[HostName]) -> None:
    _uuid_link_manager().unlink(host_names)
