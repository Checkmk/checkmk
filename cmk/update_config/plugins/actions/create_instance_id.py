#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override
from uuid import uuid4

from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.licensing.helper import get_instance_id_file_path
from cmk.utils.log import VERBOSE
from cmk.utils.paths import omd_root as _omd_root


class UpdateInstanceID(UpdateAction):
    """Ensure that instance ids are available on all sites.

    This typically happen on site creation, but it is technically possible for a raw edition that
    has never been started since the 2.2 to lack these."""

    @override
    def __call__(self, logger: Logger, omd_root: Path | None = None) -> None:
        if omd_root is None:
            omd_root = Path(_omd_root)

        if not (instance_id_file_path := get_instance_id_file_path(omd_root)).exists():
            logger.log(VERBOSE, "Creating instance ID.")
            instance_id_file_path.parent.mkdir(parents=True, exist_ok=True)
            instance_id_file_path.write_text(str(uuid4()))


UPDATE_INSTANCE_ID = UpdateInstanceID(
    name="instance_id",
    title="Create instance ID",
    sort_index=700,  # Run anywhere
    expiry_version=ExpiryVersion.CMK_300,
)

update_action_registry.register(UPDATE_INSTANCE_ID)
