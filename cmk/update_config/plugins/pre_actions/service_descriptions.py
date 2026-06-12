#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from logging import Logger
from pathlib import Path
from typing import override

from cmk.base.config import get_config_file_paths, get_default_config
from cmk.gui.exceptions import MKUserError
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction
from cmk.utils.check_utils import maincheckify

_VARNAME = "service_descriptions"


def find_outdated_entries(config_file_paths: Sequence[Path]) -> Sequence[str]:
    """Find 'service_descriptions' entries that use pre-2.0 check plug-in names.

    Every config file is evaluated in isolation against the default
    configuration, so that the reported entries can be attributed to the file
    that defines them.
    """
    issues = []
    for path in config_file_paths:
        try:
            text = path.read_text()
        except OSError:
            continue
        if _VARNAME not in text:
            continue

        context: dict[str, object] = {**get_default_config(), "FOLDER_PATH": None}
        try:
            exec(compile(text, path, "exec"), context, context)  # nosec B102 # BNS:aee528
        except Exception as e:
            # Unreadable config file -- should never happen.
            issues.append(
                f"{path}: could not be analyzed ({e}). "
                f"Please check its {_VARNAME!r} entries manually."
            )
            continue

        if not isinstance(service_descriptions := context[_VARNAME], Mapping):
            # Should also not be possible. But deal with it gracefully.
            issues.append(f"{path}: {_VARNAME!r} must be a dictionary")
            continue

        for key, value in service_descriptions.items():
            if not isinstance(key, str):
                issues.append(f"{path}: the key {key!r} must be a string")
                continue
            if (new_key := maincheckify(key)) != key:
                issues.append(f"{path}: rename {key!r} to {new_key!r}")
            if not isinstance(value, str):
                issues.append(f"{path}: the value for {key!r} must be a string")

    return issues


class CheckServiceDescriptionsPluginNames(PreUpdateAction):
    @staticmethod
    def _continue_per_users_choice(conflict_mode: ConflictMode) -> bool:
        match conflict_mode:
            case ConflictMode.FORCE:
                return True
            case ConflictMode.ABORT:
                return False
            case ConflictMode.ASK:
                return continue_per_users_choice(
                    "You can abort the update process (A) and fix the listed "
                    "entries or continue the update (c).\n"
                    "Abort update? [A/c]\n"
                ).is_not_abort()

    @override
    def __call__(
        self,
        logger: Logger,
        conflict_mode: ConflictMode,
        config_file_paths: Sequence[Path] | None = None,
    ) -> None:
        if config_file_paths is None:
            config_file_paths = get_config_file_paths(with_conf_d=True)

        if not (issues := find_outdated_entries(config_file_paths)):
            return

        issue_list = "\n".join(f"  {issue}" for issue in issues)
        logger.warning(
            f"Some {_VARNAME!r} entries in your configuration files use check "
            "plug-in names from before Checkmk version 2.0. These names are no "
            "longer translated automatically. If you do not fix the following "
            "entries, the affected services will change their names:\n"
            f"{issue_list}"
        )
        if not self._continue_per_users_choice(conflict_mode):
            raise MKUserError(None, f"Outdated check plug-in names in {_VARNAME!r}")


action = CheckServiceDescriptionsPluginNames(
    name="service_descriptions_plugin_names",
    title="Check for outdated plug-in names in 'service_descriptions'",
    sort_index=5,
    expiry_version=ExpiryVersion.CMK_310,
)
pre_update_action_registry.register(action)
