#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.werks import load as load_werks
from cmk.utils.werks.acknowledgement import load_acknowledgements, write_unacknowledged_werks
from cmk.werks.models import Compatibility, WerkV2, WerkV3

# we only ship the werks of the current major version with checkmk.
# a user might have unacknowledged werks before updating
# the information which werks are unacknowledged would vanish without this update action.
# so we look at the old version and configuration, read all unacknowledged werks
# and save those werks, so the user can still feel bad that they did not acknowledge
# those incompatible werks.
#
# to accomplish that we have to store some of the data twice:
# 1. we have to store the content of the incompatible werks of the previous major version in the
#    local site structure
# 2. we have to store the acknowledged werks.
# because a werk can be assigned multiple major versions, we have to store the acknowledged werks,
# as otherwise the user might have to acknowledge a werk multiple times for the different major
# versions.
#
# we added the code to load the werks from the site data in 2.5.0. but to make it work we
# also had to backpick this action to 2.4.0,  but 2.4.0 will not read it.
#
# from 2.5.0 on the content of unacknowledged_werks.json will be considered when displaying the
# werks browser in checkmk.
#
# when updating to a new patch release in 2.5.0 this update action will automatically remove werks
# that got acknowledged from unacknowledged_werks.json
#
# this approach means, that we might have too many werks in unacknowledged_werks.json as the customer
# already acknowledged them, but unacknowledged_werks.json is only cleaned up with the next update.
# but by accepting this, we can make this an "update only" change. all other logic does not have to
# be altered except the loading of the werks.
#
# see also: werk #15365

Werks = dict[int, WerkV2 | WerkV3]


def load_unacknowledged_werks(acknowledged_werks: set[int], werks: Werks) -> Werks:
    unacknowledged_werks = {
        **{w.id: w for w in werks.values() if w.compatible == Compatibility.NOT_COMPATIBLE},
    }
    return {id: werk for id, werk in unacknowledged_werks.items() if id not in acknowledged_werks}


class UnacknowledgedWerks(UpdateAction):
    @override
    def __call__(
        self,
        logger: Logger,
        *,
        acknowledged_werks_mk: Path | None = None,
        unacknowledged_werks_json: Path | None = None,
        compiled_werks_folder: Path | None = None,
    ) -> None:
        unacknowledged_werks = load_unacknowledged_werks(
            load_acknowledgements(
                acknowledged_werks_mk=acknowledged_werks_mk,
            ),
            load_werks(
                base_dir=compiled_werks_folder,
                unacknowledged_werks_json=unacknowledged_werks_json,
                acknowledged_werks_mk=acknowledged_werks_mk,
            ),
        )
        write_unacknowledged_werks(
            unacknowledged_werks,
            unacknowledged_werks_json=unacknowledged_werks_json,
        )


update_action_registry.register(
    UnacknowledgedWerks(
        name="store_unacknowledged_werks",
        title="Storing unacknowledged werks",
        sort_index=41,
        expiry_version=ExpiryVersion.NEVER,
    )
)
