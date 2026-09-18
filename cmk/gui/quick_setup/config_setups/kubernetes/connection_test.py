#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from functools import partial
from html import escape

from cmk.automations.results import DiagSpecialAgentInput, DiagSpecialAgentResult
from cmk.ccc.site import omd_site
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.quick_setup.v0_unstable.predefined._common import create_diag_special_agent_input
from cmk.gui.quick_setup.v0_unstable.setups import ProgressLogger, StepStatus
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
)
from cmk.gui.watolib.automations import MKAutomationException
from cmk.gui.watolib.check_mk_automations import diag_special_agent
from cmk.password_store.v1 import Secret
from cmk.utils.automation_config import LocalAutomationConfig

from .constants import QUICK_SETUP_ID
from .settings import PullSettings, read_settings


def validate_pull_connection(
    _quick_setup_id: QuickSetupId,
    data: ParsedFormData,
    progress_logger: ProgressLogger,
    *,
    run_diagnostic: Callable[[DiagSpecialAgentInput], DiagSpecialAgentResult] = partial(
        diag_special_agent, LocalAutomationConfig(), debug=False
    ),
) -> GeneralStageErrors:
    """Run the real pull agent with an ad-hoc secret on the selected monitoring site."""
    settings = read_settings(data, default_site=omd_site())
    if not isinstance(settings, PullSettings) or settings.common.site_id != omd_site():
        raise ValueError(
            "The pull connection test must run on the selected monitoring site in pull mode"
        )
    if not settings.base_url or not settings.shared_secret:
        return [_("A pull mode base URL and shared secret are required to test the connection.")]
    user.need_permission("wato.edit_all_passwords")
    progress_logger.log_new_progress_step(
        "test_pull_connection", _("Retrieve Kubernetes agent sections")
    )
    password_id = f"{settings.common.bundle_id}_pull_secret"
    result: DiagSpecialAgentResult | None
    try:
        result = run_diagnostic(
            create_diag_special_agent_input(
                rulespec_name=QUICK_SETUP_ID,
                host_name=settings.common.monitoring.host_name,
                relay_id=None,
                passwords={password_id: Secret(settings.shared_secret)},
                params={
                    "url": settings.base_url.rstrip("/"),
                    "shared_secret": ("cmk_postprocessed", "stored_password", (password_id, "")),
                    "verify_cert": True,
                },
            )
        )
    except MKAutomationException:
        # Automation failures can contain command input, including the temporary credential.
        result = None
    if (
        result is None
        or not result.results
        or any(item.return_code != 0 for item in result.results)
    ):
        progress_logger.update_progress_step_status("test_pull_connection", StepStatus.ERROR)
        return [
            _(
                "The connection test failed on monitoring site %(site)s. "
                "Check var/log/automation-helper/automation-helper.log on that site for the "
                "underlying error, then retry or skip the test."
            )
            % {"site": escape(settings.common.site_id)}
        ]
    if not any(
        line.startswith("<<<kube_") and line.endswith(">>>")
        for item in result.results
        for line in item.response.splitlines()
    ):
        progress_logger.update_progress_step_status("test_pull_connection", StepStatus.ERROR)
        return [
            _(
                "The endpoint responded, but returned no Kubernetes agent sections. "
                "Check the pull mode base URL and allow the agent time to collect data."
            )
        ]
    progress_logger.update_progress_step_status("test_pull_connection", StepStatus.COMPLETED)
    return []
