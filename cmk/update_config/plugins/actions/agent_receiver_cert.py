#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from logging import Logger

from cmk.utils.paths import omd_root

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class DeleteOldAgentReceiverCert(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        (omd_root / "etc/ssl/agent_receiver_cert.pem").unlink(missing_ok=True)


update_action_registry.register(
    DeleteOldAgentReceiverCert(
        name="agent_receiver_cert",
        title="Delete old dedicated agent receiver cert",
        sort_index=80,  # I am not aware of any constrains
    )
)
