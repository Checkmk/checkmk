#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
import shutil
from logging import Logger
from pathlib import Path

from cmk.utils import tty

from cmk.gui.watolib.paths import wato_var_dir

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class SanitizeAuditLog(UpdateAction):  # pylint: disable=too-few-public-methods
    def __init__(self, name: str, title: str, sort_index: int) -> None:
        super().__init__(name=name, title=title, sort_index=sort_index)
        self._audit_log_path: Path = wato_var_dir() / "log"

    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        # Don't run on every update!
        # Use a file to determine if the sanitization was successfull
        update_flag = self._audit_log_path / ".werk-17056"
        if update_flag.is_file():
            logger.debug("Skipping (already done)")
            return

        if not (audit_log_files := list(self._audit_log_path.glob("wato_audit.*"))):
            logger.debug("Skipping (nothing to do)")
            update_flag.touch(mode=0o660)
            return

        self._backup_source_logs(logger, audit_log_files)

        for file in audit_log_files:
            file_path = self._audit_log_path / file.name
            if not file.name.startswith("wato_audit"):
                logger.debug(f"Skipping none audit log file {file_path}")
                continue

            with open(file_path, "rb") as log_file:
                content = log_file.read().decode("utf-8")

            if "automation_secret" not in content:
                logger.debug(f"Nothing to sanitize in {file_path}")
                continue

            self._sanitize_log(content, logger, file.name, file_path)

        update_flag.touch(mode=0o660)
        logger.debug(f"Wrote sanitization flag file {update_flag}")

    def _backup_source_logs(
        self,
        logger: Logger,
        audit_log_files: list[Path],
    ) -> None:
        backup_dir = Path.home() / "audit_log_backup"
        backup_dir.mkdir(mode=0o750, exist_ok=True)
        for l in audit_log_files:
            shutil.copy(src=l, dst=backup_dir / l.name)

        logger.info(
            f"{tty.yellow}Wrote audit log backup to {backup_dir}. Please check "
            f"if the audit log in the GUI works as expected. In case of problems "
            f"you can copy the backup files back to {self._audit_log_path}. "
            f"Please check the corresponding files in {self._audit_log_path} for "
            f"any leftover automation secrets and remove them if necessary. If "
            f"everything works as expected you can remove the backup. For further "
            f"details please have a look at Werk #17056.{tty.normal}"
        )

    def _sanitize_log(self, content: str, logger: Logger, filename: str, file_path: Path) -> None:
        logger.debug(f"Start sanitize of {file_path}")

        pattern = r'Value of "automation_secret" changed from "[^"]*" to "[^"]*"\.?(\\n)?'
        modified_content = re.sub(pattern, "", content)
        with open(file_path, "wb") as file:
            file.write(modified_content.encode("utf-8"))

        logger.debug(f"Finished sanitize of {file_path}")


update_action_registry.register(
    SanitizeAuditLog(
        name="sanitize_audit_log",
        title="Sanitize audit log",
        sort_index=131,
    )
)
