#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

import cmk.utils.paths
from cmk.ccc.site import omd_site
from cmk.ruleset_matcher.labels import BuiltinLabelsKey, update_builtin_host_labels
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry


class CreateBuiltinHostLabelsFile(UpdateAction):
    """Write the ``cmk/site`` builtin host label on existing sites.

    New sites get it seeded at creation and every core restart/reload (re)writes it,
    but an existing site upgrading needs it so the label is available before activation.
    The managed-services ``cmk/customer`` label is added by a separate, edition-shipped update
    action.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        update_builtin_host_labels(
            cmk.utils.paths.builtin_host_labels_file, {BuiltinLabelsKey.SITE: str(omd_site())}
        )


update_action_registry.register(
    CreateBuiltinHostLabelsFile(
        name="create_builtin_host_labels_file",
        title="Create builtin host labels file",
        sort_index=101,  # no ordering constraints
        expiry_version=ExpiryVersion.CMK_310,
    )
)
