#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.validate_config import validate_mk_files


class ValidateConfigFiles(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        result = validate_mk_files(make_folder_tree(active_config))
        if result.logs_invalid:
            log_prefix = " " * 7
            logger.info(
                "\n%(log_prefix)sWe have identified an issue with the configuration of your site.\n\n%(log_prefix)sCurrently, this is a warning to make you aware of a potential problem.\n%(log_prefix)sOur validation process checks your configuration files against a work-in-progress internal representation.\n%(log_prefix)sIn this case, we found at least one mismatch between the two.\n\n%(log_prefix)sFor now you can proceed with the update of your site.\n%(log_prefix)sHowever, in the future we will treat this as an error and stop the update procedure.\n%(log_prefix)sTo prevent any interruptions, we kindly ask you to notify us about this issue.\n\n%(log_prefix)sPlease send us a support ticket if you believe there are no issues with your relevant configuration mk files.\n%(log_prefix)sBe sure to include the name of the configuration file, the displayed error message and \n%(log_prefix)sif possible the mk file itself.\n%(log_prefix)sThis information will help us investigate further and determine whether improvements are needed.\n\n%(log_prefix)sThe following mk files had issues during the validation:\n",
                {"log_prefix": log_prefix},
            )
            for message in result.logs_invalid:
                logger.info(
                    "%(log_prefix)s  %(message)s", {"log_prefix": log_prefix, "message": message}
                )


update_action_registry.register(
    ValidateConfigFiles(
        name="validate_config_files",
        title="Validating configuration files",
        sort_index=998,  # Should be run after any mk file modifications.
        expiry_version=ExpiryVersion.NEVER,
        continue_on_failure=True,
    )
)
