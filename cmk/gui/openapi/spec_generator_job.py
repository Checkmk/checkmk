#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from contextlib import suppress

from cmk.gui import hooks
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobAlreadyRunning,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
)
from cmk.gui.i18n import _


def register(job_registry: BackgroundJobRegistry) -> None:
    job_registry.register(SpecGeneratorBackgroundJob)
    hooks.register_builtin("tags-changed", _trigger_spec_generation_in_background)
    hooks.register_builtin("mkp-changed", _trigger_spec_generation_in_background)


def _trigger_spec_generation_in_background() -> None:
    job = SpecGeneratorBackgroundJob()
    with suppress(BackgroundJobAlreadyRunning):
        job.start(_generate_spec_in_background_job)


class SpecGeneratorBackgroundJob(BackgroundJob):
    job_prefix = "spec_generator"

    @classmethod
    def gui_title(cls) -> str:
        return _("Generate REST API specification")

    def __init__(self) -> None:
        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                stoppable=False,
                lock_wato=False,
            ),
        )


def _generate_spec_in_background_job(job_interface: BackgroundProcessInterface) -> None:
    job_interface.send_progress_update(_("Generating REST API specification"))
    with subprocess.Popen(
        ["cmk-compute-api-spec"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8"
    ) as p:
        output = p.communicate()[0]
        if p.returncode != 0:
            job_interface.send_result_message(
                _("Failed to generate REST API specification: %s") % output
            )
            return
    job_interface.send_result_message(_("REST API specification successfully generated"))
