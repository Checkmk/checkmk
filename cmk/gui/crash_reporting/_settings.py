#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.valuespec import EmailAddress, HTTPUrl, Optional, TextInput
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSupport

ConfigVariableCrashReportURL = ConfigVariable(
    group=ConfigVariableGroupSupport,
    primary_domain=ConfigDomainGUI,
    ident="crash_report_url",
    valuespec=lambda context: HTTPUrl(
        title=_("Crash report HTTP URL"),
        help=_("By default, crash reports will be sent to our crash reporting server."),
        show_as_link=False,
    ),
)

ConfigVariableCrashReportTarget = ConfigVariable(
    group=ConfigVariableGroupSupport,
    primary_domain=ConfigDomainGUI,
    ident="crash_report_target",
    valuespec=lambda context: TextInput(
        title=_("Crash report fallback mail address"),
        help=_(
            "By default, crash reports will be sent to our crash reporting server. In case "
            "this fails for some reason, the crash reports can be sent by mail to the "
            "address configured here."
        ),
        size=80,
    ),
)


def _prefilled_contact_email() -> str:
    email = user.email
    return email if email and "@" in email else ""


ConfigVariableAutomaticCrashReportUpload = ConfigVariable(
    group=ConfigVariableGroupSupport,
    primary_domain=ConfigDomainGUI,
    ident="automatic_crash_report_upload",
    valuespec=lambda context: Optional(
        # allow_empty=False is what makes "enabled but no address" unsaveable:
        # TextInput skips its regex check for the empty string.
        valuespec=EmailAddress(
            label=_("Contact email address"),
            allow_empty=False,
            default_value=_prefilled_contact_email,
        ),
        title=_("Automatic crash report upload"),
        label=_("Upload crash reports automatically"),
        none_label=_("(disabled)"),
        help=_(
            "When enabled, this site regularly uploads its crash reports to the configured "
            "crash report URL. Crash reports can contain host names, IP addresses, "
            "configuration excerpts, agent output and Python tracebacks. The contact address "
            "is sent with every report so we can follow up."
        ),
    ),
)
