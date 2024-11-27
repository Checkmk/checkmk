#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

from cmk.gui import hooks
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
)
from cmk.gui.i18n import _
from cmk.gui.logged_in import user


def register(job_registry: BackgroundJobRegistry) -> None:
    job_registry.register(SpecGeneratorBackgroundJob)
    hooks.register_builtin(
        "tags-changed",
        lambda: trigger_spec_generation_in_background(str(user.id) if user.id else None),
    )
    hooks.register_builtin(
        "mkp-changed",
        lambda: trigger_spec_generation_in_background(str(user.id) if user.id else None),
    )


def trigger_spec_generation_in_background(user_id: str | None) -> None:
    SpecGeneratorBackgroundJob().start(
        _generate_spec_in_background_job,
        InitialStatusArgs(
            title=SpecGeneratorBackgroundJob.gui_title(),
            stoppable=False,
            lock_wato=False,
            user=user_id,
        ),
    )


class SpecGeneratorBackgroundJob(BackgroundJob):
    job_prefix = "spec_generator"

    @classmethod
    def gui_title(cls) -> str:
        return _("Generate REST API specification")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)


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
