#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from logging import Logger
from pathlib import Path
from typing import override

from cmk.gui.exceptions import MKUserError
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction
from cmk.utils.paths import local_web_dir, web_dir

# Patterns that indicate a page handler registration with ident "welcome"
_REGISTRATION_PATTERNS = [
    # page_registry.register(PageEndpoint("welcome", ...))
    re.compile(r"""page_registry\s*\.\s*register\s*\(\s*PageEndpoint\s*\(\s*["']welcome["']"""),
    # Legacy pattern: pagehandlers["welcome"] = ...
    re.compile(r"""pagehandlers\s*\[\s*["']welcome["']\s*\]"""),
    # Legacy pattern: pagehandlers.update({"welcome": ...})
    re.compile(r"""pagehandlers\s*\.\s*update\s*\(\s*\{[^}]*["']welcome["']"""),
]


def _scan_file_for_welcome_registration(path: Path) -> bool:
    """Check if a plugin file registers a page handler with ident 'welcome'."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    return any(pattern.search(content) for pattern in _REGISTRATION_PATTERNS)


class PreUpdateWelcomePageConflict(PreUpdateAction):
    """Detect local page plugins that would conflict with the new built-in welcome page"""

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        conflicting_files: list[Path] = []

        for plugins_dir in [
            web_dir / "plugins" / "pages",
            local_web_dir / "plugins" / "pages",
        ]:
            if not plugins_dir.exists():
                continue

            for file_path in sorted(plugins_dir.iterdir()):
                if file_path.suffix != ".py":
                    continue
                if _scan_file_for_welcome_registration(file_path):
                    conflicting_files.append(file_path)

        if not conflicting_files:
            return

        files_list = "\n".join(f"  - {f}" for f in conflicting_files)
        logger.error(
            "Checkmk 2.5 introduces a built-in welcome page served at 'welcome.py'.\n"
            "The following local plugin file(s) register a page handler with the same\n"
            "identifier 'welcome', which would conflict with the new built-in page:\n\n"
            f"{files_list}\n\n"
            "Please rename the page handler identifier in the affected file(s) to\n"
            "avoid the conflict (e.g. change the registration ident from 'welcome'\n"
            "to 'my_welcome' so it is served at 'my_welcome.py' instead).\n"
        )
        if _continue_on_welcome_conflict(conflict_mode).is_abort():
            raise MKUserError(None, "conflicting local 'welcome' page handler")


def _continue_on_welcome_conflict(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) and rename the conflicting page\n"
                "handler, or continue the update (c). Note that the conflicting page\n"
                "handlers may cause unpredictable behavior at 'welcome.py'.\n\n"
                "Abort the update process? [A/c] \n",
            )


pre_update_action_registry.register(
    PreUpdateWelcomePageConflict(
        name="welcome_page_conflict",
        title="Welcome page conflict detection",
        sort_index=21,
        expiry_version=ExpiryVersion.CMK_260,
    )
)
