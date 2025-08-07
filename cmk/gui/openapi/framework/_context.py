#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Self

from livestatus import SiteConfigurations

from cmk.gui.config import Config
from cmk.gui.type_defs import AgentControllerCertificates, PasswordPolicy

from .api_config import APIVersion


@dataclass(kw_only=True, slots=True, frozen=True)
class ApiConfig:
    """Contains parts of the configuration that are relevant for API endpoints."""

    # Feel free to add more values here, if required. We don't want to use the `active_config`.
    # But we also want to limit this to values that are actually used throughout the API.
    agent_controller_certificates: AgentControllerCertificates
    debug: bool
    password_policy: PasswordPolicy
    sites: SiteConfigurations
    wato_max_snapshots: int
    wato_pprint_config: bool
    wato_use_git: bool

    @classmethod
    def from_config(cls, config: Config) -> Self:
        return cls(
            agent_controller_certificates=config.agent_controller_certificates,
            debug=config.debug,
            password_policy=config.password_policy,
            sites=config.sites,
            wato_max_snapshots=config.wato_max_snapshots,
            wato_pprint_config=config.wato_pprint_config,
            wato_use_git=config.wato_use_git,
        )


@dataclass(kw_only=True, slots=True, frozen=True)
class ApiContext:
    config: ApiConfig
    version: APIVersion

    @classmethod
    def new(cls, config: Config, version: APIVersion) -> Self:
        return cls(config=ApiConfig.from_config(config), version=version)
