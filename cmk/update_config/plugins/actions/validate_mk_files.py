#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.validate_config import validate_mk_files


class ValidateConfigFiles(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        result = validate_mk_files()
        if result.logs_invalid:
            log_prefix = " " * 7
            logger.info(
                "\n%sWe have identified an issue with the configuration of your site.\n\n%sCurrently, this is a warning to make you aware of a potential problem.\n%sOur validation process checks your configuration files against a work-in-progress internal representation.\n%sIn this case, we found at least one mismatch between the two.\n\n%sFor now you can proceed with the update of your site.\n%sHowever, in the future we will treat this as an error and stop the update procedure.\n%sTo prevent any interruptions, we kindly ask you to notify us about this issue.\n\n%sPlease send us a support ticket if you believe there are no issues with your relevant configuration mk files.\n%sBe sure to include the name of the configuration file, the displayed error message and \n%sif possible the mk file itself.\n%sThis information will help us investigate further and determine whether improvements are needed.\n\n%sThe following mk files had issues during the validation:\n",
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
                log_prefix,
            )
            for message in result.logs_invalid:
                logger.info("%s  %s", log_prefix, message)


update_action_registry.register(
    ValidateConfigFiles(
        name="validate_config_files",
        title="Validating configuration files",
        sort_index=998,  # Should be run after any mk file modifications.
        expiry_version=ExpiryVersion.NEVER,
        continue_on_failure=True,
    )
)
