#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger

from cmk.utils.log import VERBOSE

from cmk.gui.exceptions import MKUserError
from cmk.gui.session import SuperUserContext
from cmk.gui.watolib.hosts_and_folders import FolderTree, Host

from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


def _continue_per_users_choice(conflict_mode: ConflictMode, msg: str) -> bool:
    match conflict_mode:
        case ConflictMode.FORCE | ConflictMode.INSTALL:
            return True
        case ConflictMode.ABORT | ConflictMode.KEEP_OLD:
            return False
        case ConflictMode.ASK:
            return continue_per_users_choice(msg).is_not_abort()


def _remove_labels(host: Host, invalid_labels: set[str]) -> None:
    updated_labels = {
        k: v for k, v in host.attributes.get("labels", {}).items() if k not in invalid_labels
    }
    with SuperUserContext():
        host.update_attributes({"labels": updated_labels})


def _find_invalid_labels() -> dict[Host, set[str]]:
    result: dict[Host, set[str]] = {}

    for folder_path, folder in FolderTree().all_folders().items():
        hosts = folder.hosts()
        for host_name, host in hosts.items():
            labels = host.labels()
            invalid_labels = set()
            for label, value in labels.items():
                if ":" in label or ":" in value:
                    invalid_labels.add(label)

            if invalid_labels:
                result[host] = invalid_labels
    return result


class RemoveInvalidHostLabels(PreUpdateAction):
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        hosts_to_fix = _find_invalid_labels()

        if not hosts_to_fix:
            return

        if not _continue_per_users_choice(
            conflict_mode,
            f"{len(hosts_to_fix)} hosts contain labels with `:` as part of the name or the value, which is not allowed. "
            "If you continue, the affected label(s) will be removed. "
            "Abort the update process? [A/c] \n",
        ):
            raise MKUserError(None, "The user cancelled the deletion of invalid labels.")

        for host, invalid_labels in hosts_to_fix.items():
            _remove_labels(host, invalid_labels)
            logger.log(
                VERBOSE,
                f"{host.folder().path()}/{host.name()} - labels removed: {', '.join(invalid_labels)}",
            )


pre_update_action_registry.register(
    RemoveInvalidHostLabels(
        name="remove_invalid_host_labels",
        title="Remove invalid hosts labels",
        sort_index=50,
    )
)
