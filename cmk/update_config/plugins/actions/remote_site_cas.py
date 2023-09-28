#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

import cmk.utils.paths

from cmk.gui.watolib.config_domains import ConfigDomainCACertificates

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateRemoteSitesCAs(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        unfiltered_raw_certs = cmk.utils.paths.trusted_ca_file.read_text().split("\n\n")
        valid_raw_certs = [
            raw for raw in unfiltered_raw_certs if ConfigDomainCACertificates.is_valid_cert(raw)
        ]
        if len(unfiltered_raw_certs) != len(valid_raw_certs):
            logger.info("Removing invalid data from %s", cmk.utils.paths.trusted_ca_file.name)
        cmk.utils.paths.trusted_ca_file.write_text("\n\n".join(valid_raw_certs))
        ConfigDomainCACertificates.update_remote_sites_cas(valid_raw_certs)


update_action_registry.register(
    UpdateRemoteSitesCAs(
        name="remote_site_cas",
        title="Extract remote sites CAs",
        sort_index=80,  # I am not aware of any constrains
    )
)
