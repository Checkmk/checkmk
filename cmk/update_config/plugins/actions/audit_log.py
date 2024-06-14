#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from logging import Logger
from pathlib import Path

from typing_extensions import Buffer

from cmk.utils.exceptions import MKException, MKGeneralException

from cmk.gui.watolib.paths import wato_var_dir

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateAuditLog(UpdateAction):  # pylint: disable=too-few-public-methods
    def __init__(self, name: str, title: str, sort_index: int) -> None:
        super().__init__(name=name, title=title, sort_index=sort_index)
        self._audit_log_path: Path = wato_var_dir() / "log" / "wato_audit.log"
        self._audit_log_backup_path: Path = wato_var_dir() / "log" / "wato_audit.log-backup"
        self._audit_log_target_size: int = 300 * 1024 * 1024  # 300MB in bytes

    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        if not self._audit_log_path.exists():
            logger.debug("No audit log found. Skipping...")
            return

        if self._audit_log_path.stat().st_size <= self._audit_log_target_size:
            logger.debug("Audit log small enough. Skipping...")
            return

        logger.debug("Start backup of existing audit log")
        self._backup_source_log()
        logger.debug("Finished backup of existing audit log")

        logger.debug("Start splitting of existing audit log")
        logger_msg = "Skipping update of audit log. Please review the errors and try 'cmk-update-config' again"
        try:
            self._split_file(wato_var_dir() / "log")
        except IOError as e:
            logger.warning(logger_msg)
            raise MKException(
                f"I/O error while updating existing audit log({e.errno}): {e.strerror}"
            ) from e
        except Exception as msg:
            logger.warning(logger_msg)
            raise MKGeneralException(f"Unknown error while updating audit log: {msg}") from msg
        logger.debug("Finished splitting of existing audit log")

        logger.debug("Start clearing existing audit log")
        self._clear_source_log()
        logger.debug("Finished clearing existing audit log")

    def _backup_source_log(self) -> None:
        self._audit_log_backup_path.write_text(self._audit_log_path.read_text())

    def _split_file(self, output_dir: Path) -> None:
        with open(self._audit_log_path, "rb") as source_file:
            source_content = source_file.read()

        lines = source_content.split(b"\0")

        suffix = time.strftime("%Y-%m-%d")
        current_file = 0
        current_size = 0
        current_lines: list[Buffer] = []

        for line in lines:
            line_size = len(line) + 1

            if current_size + line_size > self._audit_log_target_size:
                output_file_path = output_dir / f"wato_audit.log.{suffix}"
                with open(output_file_path, "wb") as output_file:
                    output_file.write(b"\0".join(current_lines))
                current_file += 1
                current_lines = []
                current_size = 0
                suffix = (
                    f"{suffix[:-1]}{current_file}"
                    if suffix[-2] == "-"
                    else f"{suffix}-{current_file}"
                )

            current_lines.append(line)
            current_size += line_size

        if current_lines:
            output_file_path = output_dir / f"wato_audit.log.{suffix}"
            with open(output_file_path, "wb") as output_file:
                output_file.write(b"\0".join(current_lines))

    def _clear_source_log(self) -> None:
        self._audit_log_path.write_text("")


update_action_registry.register(
    UpdateAuditLog(
        name="update_audit_log",
        title="Split large audit logs",
        sort_index=130,
    )
)
