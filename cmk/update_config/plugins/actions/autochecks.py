#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.update_config.plugins.lib.autochecks import rewrite_yielding_errors
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateAutochecks(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        # just consume to trigger rewriting. We already warned in pre-action.
        for _error in rewrite_yielding_errors(write=True):
            pass


update_action_registry.register(
    UpdateAutochecks(
        name="autochecks",
        title="Autochecks",
        sort_index=40,
    )
)
