#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (  # pylint: disable=unused-import
    Text, List, Optional,
)
#TODO included in typing since Python >= 3.8
from typing_extensions import TypedDict

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import HTTPRedirect
import cmk.gui.config as config
from cmk.gui.valuespec import (  # pylint: disable=unused-import
    ValueSpec, Dictionary, ListChoice, FixedValue, DropdownChoice,
)
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.background_job import BackgroundProcessInterface  # pylint: disable=unused-import
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob
from cmk.gui.watolib.automations import check_mk_automation

from cmk.gui.plugins.wato.utils.context_buttons import home_button

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
)

DiagnosticsParams = TypedDict("DiagnosticsParams", {
    "site": str,
    "general": None,
    "opt_info": List,
})


@mode_registry.register
class ModeDiagnostics(WatoMode):
    @classmethod
    def name(cls):
        # type: () -> str
        return "diagnostics"

    @classmethod
    def permissions(cls):
        # type : () -> List[str]
        return ["diagnostics"]

    def _from_vars(self):
        # type: () -> None
        self._start = bool(html.request.get_ascii_input("_start"))
        self._diagnostics_params = self._get_diagnostics_params()
        self._job = DiagnosticsDumpBackgroundJob()

    def _get_diagnostics_params(self):
        # type: () -> Optional[DiagnosticsParams]
        if self._start:
            return self._vs_diagnostics().from_html_vars("diagnostics")
        return None

    def title(self):
        # type: () -> Text
        return _("Diagnostics")

    def buttons(self):
        # type: () -> None
        home_button()

    def action(self):
        # type: () -> None
        if not html.check_transaction():
            return

        if self._job.is_active() or self._diagnostics_params is None:
            raise HTTPRedirect(self._job.detail_url())

        self._job.set_function(self._job.do_execute, self._diagnostics_params)
        self._job.start()

        raise HTTPRedirect(self._job.detail_url())

    def page(self):
        # type: () -> None
        job_status_snapshot = self._job.get_status_snapshot()
        if job_status_snapshot.is_active():
            raise HTTPRedirect(self._job.detail_url())

        html.begin_form("diagnostics", method="POST")

        vs_diagnostics = self._vs_diagnostics()
        vs_diagnostics.render_input("diagnostics", {})

        html.button("_start", _("Start"))
        html.hidden_fields()
        html.end_form()

    def _vs_diagnostics(self):
        # type: () -> ValueSpec
        return Dictionary(
            title=_("Collect diagnostic dump"),
            render="form",
            elements=[
                ("site", DropdownChoice(
                    title=_("Site"),
                    choices=config.get_wato_site_choices(),
                )),
                ("general",
                 FixedValue(None,
                            totext=_("Collect information about OS and Checkmk version"),
                            title=_("General information"))),
                ("opt_info", ListChoice(
                    title=_("Optional information"),
                    choices=[],
                )),
            ],
            optional_keys=False,
        )


@gui_background_job.job_registry.register
class DiagnosticsDumpBackgroundJob(WatoBackgroundJob):
    job_prefix = "diagnostics_dump"

    @classmethod
    def gui_title(cls):
        # type: () -> Text
        return _("Diagnostics dump")

    def __init__(self):
        # type: () -> None
        super(DiagnosticsDumpBackgroundJob, self).__init__(
            self.job_prefix,
            title=self.gui_title(),
            lock_wato=False,
            stoppable=False,
        )

    def _back_url(self):
        # type: () -> str
        return html.makeuri([])

    def do_execute(self, diagnostics_params, job_interface):
        # type: (DiagnosticsParams, BackgroundProcessInterface) -> None
        job_interface.send_progress_update(_("Diagnostics dump started..."))

        site = diagnostics_params["site"]
        timeout = html.request.request_timeout - 2
        result = check_mk_automation(site,
                                     "create-diagnostics-dump",
                                     timeout=timeout,
                                     non_blocking_http=True)

        job_interface.send_progress_update(result["output"])

        tarfile_path = result['tarfile_path']
        #TODO next
        #download_url = html.makeuri_contextless([("site", site)], filename=tarfile_path)
        #button = html.render_icon_button(download_url, _("Download"), "diagnostics_dump_file")

        #job_interface.send_result_message(
        #    _("Diagnostics dump file: %s %s") % (tarfile_path, button))
        job_interface.send_result_message(_("Diagnostics dump file: %s") % tarfile_path)
