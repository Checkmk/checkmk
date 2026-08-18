#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.form_specs.unstable import OptionalChoice
from cmk.gui.logged_in import user
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSupport
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Label, Title


def _validate_optional_http_url(value: str) -> None:
    """HTTPUrl valuespec has allow_empty"""
    if not value:
        return
    fs.validators.Url(protocols=[fs.validators.UrlProtocol.HTTP, fs.validators.UrlProtocol.HTTPS])(
        value
    )


ConfigVariableCrashReportURL = ConfigVariable(
    group=ConfigVariableGroupSupport,
    primary_domain=ConfigDomainGUI,
    ident="crash_report_url",
    form_spec=lambda context: fs.String(
        title=Title("Crash report HTTP URL"),
        help_text=Help("By default, crash reports will be sent to our crash reporting server."),
        field_size=fs.FieldSize.LARGE,
        custom_validate=[_validate_optional_http_url],
    ),
)

ConfigVariableCrashReportTarget = ConfigVariable(
    group=ConfigVariableGroupSupport,
    primary_domain=ConfigDomainGUI,
    ident="crash_report_target",
    form_spec=lambda context: fs.String(
        title=Title("Crash report fallback mail address"),
        help_text=Help(
            "By default, crash reports will be sent to our crash reporting server. In case "
            "this fails for some reason, the crash reports can be sent by mail to the "
            "address configured here."
        ),
        field_size=fs.FieldSize.LARGE,
    ),
)


def _prefilled_contact_email() -> str:
    email = user.email
    return email if email and "@" in email else ""


ConfigVariableAutomaticCrashReportUpload = ConfigVariable(
    group=ConfigVariableGroupSupport,
    primary_domain=ConfigDomainGUI,
    ident="automatic_crash_report_upload",
    form_spec=lambda context: OptionalChoice(
        # The EmailAddress validator is what makes "enabled but no address"
        # unsaveable: it rejects the empty string.
        parameter_form=fs.String(
            label=Label("Contact email address"),
            prefill=fs.DefaultValue(_prefilled_contact_email()),
            custom_validate=[fs.validators.EmailAddress()],
        ),
        title=Title("Automatic crash report upload"),
        label=Label("Upload crash reports automatically"),
        none_label=Label("(disabled)"),
        help_text=Help(
            "When enabled, this site uploads its crash reports once a day to the configured "
            "crash report URL. Crash reports can contain host names, IP addresses, "
            "configuration excerpts, agent output and Python tracebacks. The contact address "
            "is sent with every report so we can follow up."
        ),
    ),
)
