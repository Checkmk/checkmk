#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from cmk.utils.log import VERBOSE

from cmk.gui.config import active_config

from cmk.update_config.plugins.lib.remove_invalid_host_labels import (
    _find_invalid_labels,
    _remove_labels,
)
from cmk.update_config.registry import update_action_registry, UpdateAction


class RemoveInvalidHostLabels(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        hosts_to_fix = _find_invalid_labels()

        for host, invalid_labels in hosts_to_fix.items():
            _remove_labels(host, invalid_labels, pprint_value=active_config.wato_pprint_config)
            logger.log(
                VERBOSE,
                f"{host.folder().path()}/{host.name()} - labels removed: {', '.join(invalid_labels)}",
            )


update_action_registry.register(
    RemoveInvalidHostLabels(
        name="remove_invalid_host_labels",
        title="Remove invalid hosts labels",
        sort_index=150,
    )
)
