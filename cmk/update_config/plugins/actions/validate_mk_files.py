#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.validate_config import validate_mk_files


class ValidateConfigFiles(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        result = validate_mk_files()
        if result.logs_invalid:
            log_prefix = " " * 7
            logger.info(
                "\n"
                f"{log_prefix}We have identified an issue with the configuration of your site.\n\n"
                f"{log_prefix}Currently, this is a warning to make you aware of a potential problem.\n"
                f"{log_prefix}Our validation process checks your configuration files against a work-in-progress internal representation.\n"
                f"{log_prefix}In this case, we found at least one mismatch between the two.\n\n"
                f"{log_prefix}For now you can proceed with the update of your site.\n"
                f"{log_prefix}However, in the future we will treat this as an error and stop the update procedure.\n"
                f"{log_prefix}To prevent any interruptions, we kindly ask you to notify us about this issue.\n\n"
                f"{log_prefix}Please send us a support ticket if you believe there are no issues with your relevant configuration mk files.\n"
                f"{log_prefix}Be sure to include the name of the configuration file, the displayed error message and \n"
                f"{log_prefix}if possible the mk file itself.\n"
                f"{log_prefix}This information will help us investigate further and determine whether improvements are needed.\n\n"
                f"{log_prefix}The following mk files had issues during the validation:\n"
            )
            for message in result.logs_invalid:
                logger.info(f"{log_prefix}  {message}")


update_action_registry.register(
    ValidateConfigFiles(
        name="validate_config_files",
        title="Validating configuration files",
        sort_index=998,  # Should be run after any mk file modifications.
        continue_on_failure=True,
    )
)
