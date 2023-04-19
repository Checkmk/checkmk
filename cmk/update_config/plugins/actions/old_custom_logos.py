#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path

import cmk.utils.paths
from cmk.utils import version
from cmk.utils.exceptions import MKGeneralException

if version.is_managed_edition():
    from cmk.gui.cme.managed import (  # pylint: disable=no-name-in-module,import-error
        Customer,
        CustomerId,
        load_customers,
        save_customers,
    )

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class RemoveOldCustomLogos(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        """Remove old custom logo occurences, i.e. local image files "mk-logo.png" and customer
        config "globals" entries with key "logo"."""
        if not version.is_managed_edition():
            return

        themes_path: Path = Path(cmk.utils.paths.local_web_dir, "htdocs/themes/")
        for theme in ["facelift", "modern-dark"]:
            logo_path: Path = themes_path / theme / "images/mk-logo.png"
            if logo_path.is_file():
                logo_path.unlink()

        try:
            customers: dict[CustomerId, Customer] = load_customers()
            for config in customers.values():
                globals_config: dict[str, dict] = config.get("globals", {})
                if "logo" in globals_config:
                    del globals_config["logo"]
            save_customers(customers)
        except MKGeneralException:
            pass


update_action_registry.register(
    RemoveOldCustomLogos(
        name="custom_logos",
        title="Remove old custom logos",
        sort_index=100,
    )
)
