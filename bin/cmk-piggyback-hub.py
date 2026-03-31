#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import traceback
from typing import Literal

from cmk.ccc.crash_reporting import (  # astrein: disable=cmk-module-layer-violation
    ABCCrashReport,
    CrashReportStore,
    make_crash_report_base_path,
)
from cmk.ccc.hostaddress import (  # astrein: disable=cmk-module-layer-violation
    HostNameValidationError,
)
from cmk.ccc.version import get_general_version_infos  # astrein: disable=cmk-module-layer-violation
from cmk.piggyback.hub import main  # astrein: disable=cmk-module-layer-violation
from cmk.utils.paths import omd_root  # astrein: disable=cmk-module-layer-violation
from cmk.utils.security_event import (  # astrein: disable=cmk-module-layer-violation
    InputValidationFailureEvent,
    log_security_event,
)


class PiggybackHubCrashReport(ABCCrashReport[None]):
    @classmethod
    def type(cls) -> Literal["piggyback-hub"]:
        return "piggyback-hub"


def create_crash_report_callback() -> str:
    try:
        crash = PiggybackHubCrashReport(
            crash_report_base_path=make_crash_report_base_path(omd_root),
            crash_info=PiggybackHubCrashReport.make_crash_info(
                get_general_version_infos(omd_root), None
            ),
        )
        CrashReportStore().save(crash)
        return f"Please submit a crash report! (Crash-ID: {crash.ident_to_text()})"
    except Exception:
        return f"Failed to create a crash report: {traceback.format_exc()}"


def invalid_hostname_callback(exc: HostNameValidationError) -> None:
    log_security_event(
        InputValidationFailureEvent(
            summary="Piggyback host name rejected",
            input_value=exc.raw,
            validation_entity="HostName",
        )
    )


if __name__ == "__main__":
    sys.exit(
        main(
            sys.argv,
            crash_report_callback=create_crash_report_callback,
            invalid_hostname_callback=invalid_hostname_callback,
        )
    )
