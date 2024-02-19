#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils.exceptions import MKGeneralException

from cmk.update_config.plugins.lib.autochecks import rewrite_yielding_errors
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateAutochecks(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        failed_hosts = []

        for rewrite_error in rewrite_yielding_errors(logger):
            logger.error(rewrite_error.message)
            failed_hosts.append(rewrite_error.host_name)

        if failed_hosts:
            msg = f"Failed to rewrite autochecks file for hosts: {', '.join(failed_hosts)}"
            logger.error(msg)
            raise MKGeneralException(msg)


update_action_registry.register(
    UpdateAutochecks(
        name="autochecks",
        title="Autochecks",
        sort_index=40,
    )
)
