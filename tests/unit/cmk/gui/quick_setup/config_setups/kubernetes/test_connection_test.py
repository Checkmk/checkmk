#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.automations.results import DiagSpecialAgentInput, DiagSpecialAgentResult
from cmk.automations.results.diagnostics import SpecialAgentResult
from cmk.ccc.site import omd_site
from cmk.gui.quick_setup.config_setups.kubernetes.configuration import pull_configuration
from cmk.gui.quick_setup.config_setups.kubernetes.connection_test import validate_pull_connection
from cmk.gui.quick_setup.config_setups.kubernetes.constants import QUICK_SETUP_ID
from cmk.gui.quick_setup.config_setups.kubernetes.settings import (
    CONNECTION,
    PULL_URL,
    PullSettings,
    read_settings,
)
from cmk.gui.quick_setup.handlers.utils import InfoLogger
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.watolib.automations import MKAutomationException

pytestmark = pytest.mark.usefixtures("with_admin_login")


@pytest.fixture
def pull_data(data: ParsedFormData) -> ParsedFormData:
    return {
        **data,
        CONNECTION: ("pull", {"shared_secret": "kept-secret"}),
        PULL_URL: {"base_url": "https://agent:30050/"},
    }


def test_pull_connection_uses_saved_rule_parameters_and_an_ad_hoc_secret(
    pull_data: ParsedFormData,
) -> None:
    inputs: list[DiagSpecialAgentInput] = []

    def run_diagnostic(diag_input: DiagSpecialAgentInput) -> DiagSpecialAgentResult:
        inputs.append(diag_input)
        return DiagSpecialAgentResult([SpecialAgentResult(0, "<<<kube_pod_info:sep(0)>>>\n{}\n")])

    errors = validate_pull_connection(
        QUICK_SETUP_ID, pull_data, InfoLogger(), run_diagnostic=run_diagnostic
    )

    assert errors == []
    (diag_input,) = inputs
    settings = read_settings(pull_data, default_site=omd_site())
    assert isinstance(settings, PullSettings)
    configuration = pull_configuration(
        bundle_id=settings.common.bundle_id,
        host_name=settings.common.monitoring.host_name,
        host_path=settings.common.host_path,
        site_id=settings.common.site_id,
        base_url=settings.base_url,
        shared_secret=settings.shared_secret,
    )
    assert configuration.rules
    (rule,) = configuration.rules
    assert diag_input.params == rule["spec"]["value"]
    assert diag_input.agent_name == "kube_v2"
    assert diag_input.host_config.host_name == "production"
    assert diag_input.passwords["kubernetes_config_1_pull_secret"].reveal() == "kept-secret"


@pytest.mark.parametrize(
    "result",
    [
        pytest.param(DiagSpecialAgentResult([]), id="no-agent-command"),
        pytest.param(
            DiagSpecialAgentResult([SpecialAgentResult(1, "401 Unauthorized: kept-secret")]),
            id="request-failed",
        ),
        pytest.param(DiagSpecialAgentResult([SpecialAgentResult(0, "")]), id="empty-response"),
        pytest.param(
            DiagSpecialAgentResult([SpecialAgentResult(0, "<<<<cluster>>>>\n<<<<>>>>\n")]),
            id="piggyback-markers-without-sections",
        ),
        pytest.param(
            DiagSpecialAgentResult([SpecialAgentResult(0, "<<<check_mk>>>\nVersion: 3.0.0\n")]),
            id="not-kubernetes-sections",
        ),
        pytest.param(
            DiagSpecialAgentResult([SpecialAgentResult(0, "<html>kept-secret</html>")]),
            id="not-agent-data",
        ),
    ],
)
def test_failed_pull_test_returns_errors_without_exposing_response_credentials(
    pull_data: ParsedFormData, result: DiagSpecialAgentResult
) -> None:
    errors = validate_pull_connection(
        QUICK_SETUP_ID, pull_data, InfoLogger(), run_diagnostic=lambda _input: result
    )

    assert errors
    assert all("kept-secret" not in error for error in errors)


def test_pull_automation_failure_does_not_expose_command_input(pull_data: ParsedFormData) -> None:
    def failed_automation(_input: DiagSpecialAgentInput) -> DiagSpecialAgentResult:
        raise MKAutomationException("Command input: kept-secret")

    errors = validate_pull_connection(
        QUICK_SETUP_ID, pull_data, InfoLogger(), run_diagnostic=failed_automation
    )

    assert all("kept-secret" not in error for error in errors)
    assert omd_site() in errors[0]
    assert "var/log/automation-helper/automation-helper.log" in errors[0]


def test_pull_failure_points_to_the_site_log_without_exposing_output(
    pull_data: ParsedFormData,
) -> None:
    diagnostic = DiagSpecialAgentResult(
        [SpecialAgentResult(1, "Connection reset by peer: <script>kept-secret</script>")]
    )

    errors = validate_pull_connection(
        QUICK_SETUP_ID, pull_data, InfoLogger(), run_diagnostic=lambda _input: diagnostic
    )

    assert len(errors) == 1
    assert omd_site() in errors[0]
    assert "var/log/automation-helper/automation-helper.log" in errors[0]
    assert "Connection reset" not in errors[0]
    assert "kept-secret" not in errors[0]


@pytest.mark.parametrize("field", ["mode", "site"])
def test_pull_test_rejects_wrong_mode_or_site_before_running(
    pull_data: ParsedFormData, field: str
) -> None:
    invalid_data: dict[str, ParsedFormData] = {
        "mode": {CONNECTION: ("push", {})},
        "site": {FormSpecId("site"): {"site_selection": "another-site"}},
    }

    def unexpected_diagnostic(_input: DiagSpecialAgentInput) -> DiagSpecialAgentResult:
        pytest.fail("Do not contact the agent in push mode or from the wrong monitoring site")

    with pytest.raises(ValueError, match="selected monitoring site in pull mode"):
        validate_pull_connection(
            QUICK_SETUP_ID,
            {**pull_data, **invalid_data[field]},
            InfoLogger(),
            run_diagnostic=unexpected_diagnostic,
        )
