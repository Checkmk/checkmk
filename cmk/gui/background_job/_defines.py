#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths


class BackgroundJobDefines:
    base_dir = str(cmk.utils.paths.var_dir / "background_jobs")
    process_name = (
        "cmk-job"  # NOTE: keep this name short! psutil.Process tends to truncate long names
    )

    jobstatus_filename = "jobstatus.mk"
    progress_update_filename = "progress_update"
    exceptions_filename = "exceptions"
    result_message_filename = "result_message"
