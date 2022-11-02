#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

import cmk.utils.paths

from cmk.gui.watolib.config_domains import ConfigDomainCACertificates

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateRemoteSitesCAs(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        trusted_cas = cmk.utils.paths.trusted_ca_file.read_text().split("\n\n")
        ConfigDomainCACertificates.update_remote_sites_cas(trusted_cas)


update_action_registry.register(
    UpdateRemoteSitesCAs(
        name="remote_site_cas",
        title="Extract remote sites CAs",
        sort_index=80,  # I am not aware of any constrains
    )
)
