#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.paths import wato_var_dir

from cmk.update_config.registry import update_action_registry, UpdateAction


class WatoAuditLogConversion(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        for file_ in (wato_var_dir() / "log").glob("wato_audit.*"):
            if self.needs_conversion(file_):
                self.convert_file(file_)

    @staticmethod
    def needs_conversion(file_: Path) -> bool:
        try:
            AuditLogStore(file_).read()
        except MKUserError:
            return True
        return False

    @staticmethod
    def convert_file(file_: Path) -> None:
        with file_.open("rb") as f:
            data = f.read()
        with file_.open("wb") as f:
            f.write(data.replace(b"\0", b"\n"))


update_action_registry.register(
    WatoAuditLogConversion(
        name="wato_audit_log_converter",
        title="Convert WATO audit log to be newline separated",
        sort_index=50,
    )
)
