#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import Self

from werkzeug.datastructures import ETags

from livestatus import SiteConfigurations

from cmk.gui.config import Config
from cmk.gui.openapi.restful_objects.constructors import ETagHash, hash_of_dict
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.role_types import BuiltInUserRole, CustomUserRole
from cmk.gui.type_defs import AgentControllerCertificates, GraphTimerange, PasswordPolicy
from cmk.utils.tags import TagGroup

from .api_config import APIVersion


class ETag:
    """Represents an ETag for an object, which are used to determine if an object has changed.

    The ETag is calculated from a dict, which should contain all values that are needed to fully
    describe the state of the object."""

    __slots__ = ("_values",)

    def __init__(self, values: dict[str, object]) -> None:
        self._values = values

    def hash(self) -> ETagHash:
        """Calculate the ETag hash from the values."""
        return hash_of_dict(self._values)


@dataclass(kw_only=True, slots=True, frozen=True)
class ApiETagHandler:
    enabled: bool
    if_match: ETags

    def verify(self, etag: ETag) -> None:
        """Check if the ETag matches the If-Match header."""
        if not self.if_match:
            raise ProblemException(
                HTTPStatus.PRECONDITION_REQUIRED,
                "Precondition required",
                "If-Match header required for this operation. See documentation.",
            )

        # this is equivalent to `contains`, but we skip calculating the hash in case of a star tag
        if self.if_match.star_tag or self.if_match.is_strong(etag.hash()):
            return

        raise ProblemException(
            HTTPStatus.PRECONDITION_FAILED,
            "Precondition failed",
            f"ETag didn't match. Expected {etag}. Probable cause: Object changed by another user.",
        )


@dataclass(kw_only=True, slots=True, frozen=True)
class ApiConfig:
    """Contains parts of the configuration that are relevant for API endpoints."""

    # Feel free to add more values here, if required. We don't want to use the `active_config`.
    # But we also want to limit this to values that are actually used throughout the API.
    agent_controller_certificates: AgentControllerCertificates
    debug: bool
    graph_timeranges: list[GraphTimerange]
    password_policy: PasswordPolicy
    sites: SiteConfigurations
    tag_groups: list[TagGroup]
    wato_max_snapshots: int
    wato_pprint_config: bool
    wato_use_git: bool
    roles: Mapping[str, CustomUserRole | BuiltInUserRole]

    @classmethod
    def from_config(cls, config: Config) -> Self:
        return cls(
            agent_controller_certificates=config.agent_controller_certificates,
            debug=config.debug,
            graph_timeranges=config.graph_timeranges,
            password_policy=config.password_policy,
            sites=config.sites,
            tag_groups=config.tags.tag_groups,
            wato_max_snapshots=config.wato_max_snapshots,
            wato_pprint_config=config.wato_pprint_config,
            wato_use_git=config.wato_use_git,
            roles=config.roles,
        )


@dataclass(kw_only=True, slots=True, frozen=True)
class ApiContext:
    config: ApiConfig
    version: APIVersion
    etag: ApiETagHandler

    @classmethod
    def new(cls, config: Config, version: APIVersion, etag_if_match: ETags) -> Self:
        return cls(
            config=ApiConfig.from_config(config),
            version=version,
            etag=ApiETagHandler(
                enabled=config.rest_api_etag_locking,
                if_match=etag_if_match,
            ),
        )
