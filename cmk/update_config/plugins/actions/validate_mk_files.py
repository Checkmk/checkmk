#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils import tty
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError

from cmk.gui.watolib.simple_config_file import config_file_registry

from cmk.update_config.registry import update_action_registry, UpdateAction


class ValidateConfigFiles(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        """
        Validate the data in all registered mk config files.
        """

        failures: bool = False
        for n, relative_file_path in enumerate(config_file_registry, start=1):
            result = f"    {tty.yellow}{n:02d}{tty.normal} {relative_file_path:.<60} "
            try:
                config_file_registry[relative_file_path].read_file_and_validate()
            except (NotImplementedError, ConfigValidationError) as exc:
                result += f"{tty.red}Failed{tty.normal}\n    {str(exc)}"
                failures = True
            else:
                result += f"{tty.green}Passed{tty.normal}"

            logger.info(result)

        if failures:
            logger.info(
                "    We found an issue with the configuration of your site.\n"
                "    Currently it is just a warning to make you aware of the potential problem.\n"
                "    For now you can proceed with the update of your site.\n\n"
                "    However, in the future we will treat this as an error and stop the update procedure.\n"
                "    Because of this, it is important that you make us aware of the issue.\n"
                "    Please send us a support ticket with the information provided here so that we can work\n"
                "    out whether there is migration code missing or the validation needs to be improved.\n\n"
            )


update_action_registry.register(
    ValidateConfigFiles(
        name="validate_config_files",
        title="Validating configuration files",
        sort_index=998,  # Should be run after any mk file modifications.
        continue_on_failure=True,
    )
)
