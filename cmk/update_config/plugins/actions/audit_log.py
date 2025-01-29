#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
import shutil
import time
from logging import Logger
from pathlib import Path

from typing_extensions import Buffer

from cmk.utils import tty
from cmk.utils.exceptions import MKException, MKGeneralException

from cmk.gui.watolib.paths import wato_var_dir

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class WatoAuditLogConversion(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        audit_logs = list((wato_var_dir() / "log").glob("wato_audit.*"))
        if not self.needs_conversion(audit_logs):
            return
        for file_ in audit_logs:
            self.convert_file(file_)

    @staticmethod
    def needs_conversion(logs: list[Path]) -> bool:
        """check if we need the conversion

        1. Version loaded every audit log and made sure all were converted. This took up to 10
        minutes in old and large setups
        2. Version just loaded files until one contained entries and if that was converted we
        assumed all were converted.
        3. Version (current) we peek into the files and if one contains a "\n" we assume all are
        converted if it contains a "\0" we say we need conversion
        """

        for file_ in logs:
            with file_.open("rb") as fh:
                while data := fh.read(1024):
                    if b"\n" in data:
                        return False
                    if b"\0" in data:
                        return True
        return False

    @staticmethod
    def convert_file(file_: Path) -> None:
        with file_.open("rb") as f:
            data = f.read()
        with file_.open("wb") as f:
            f.write(data.replace(b"\0", b"\n"))


# This must go first of all audit log thingies
update_action_registry.register(
    WatoAuditLogConversion(
        name="wato_audit_log_converter",
        title="Convert WATO audit log to be newline separated",
        sort_index=10,
    )
)


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

        lines = source_content.split(b"\n")

        suffix = time.strftime("%Y-%m-%d")
        current_file = 0
        current_size = 0
        current_lines: list[Buffer] = []

        for line in lines:
            line_size = len(line) + 1

            if current_size + line_size > self._audit_log_target_size:
                output_file_path = output_dir / f"wato_audit.log.{suffix}"
                with open(output_file_path, "wb") as output_file:
                    output_file.write(b"\n".join(current_lines))
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
                output_file.write(b"\n".join(current_lines))

    def _clear_source_log(self) -> None:
        self._audit_log_path.write_text("")


update_action_registry.register(
    UpdateAuditLog(
        name="update_audit_log",
        title="Split large audit logs",
        sort_index=130,
    )
)


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
            f"if the audit log in the GUI works as expected.\nIn case of problems "
            f"you can copy the backup files back to {self._audit_log_path}.\n"
            f"Please check the corresponding files in {self._audit_log_path} for "
            f"any leftover automation secrets and remove them if necessary.\nIf "
            f"everything works as expected you can remove the backup.\nFor further "
            f"details please have a look at Werk #17056.{tty.normal}"
        )

    def _sanitize_log(self, content: str, logger: Logger, filename: str, file_path: Path) -> None:
        logger.debug(f"Start sanitize of {file_path}")

        pattern = (
            r'Value of "automation_secret" changed from "[^"]*" to "[^"]*"\.?(\\n)?|'
            r'Attribute "automation_secret" with value "[^"]*" added\.?(\\n)?'
        )

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
