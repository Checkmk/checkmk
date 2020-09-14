#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    HTTPUrl,
    TextAscii,
    Dictionary,
    TextUnicode,
)
from cmk.gui.plugins.wato.utils import (
    PasswordFromStore,)

from cmk.gui.plugins.wato import (
    config_variable_group_registry,
    ConfigVariableGroup,
    config_variable_registry,
    ConfigVariable,
    ConfigDomainGUI,
)


@config_variable_group_registry.register
class ConfigVariableGroupSupport(ConfigVariableGroup):
    def title(self):
        return _('Support')

    def sort_index(self):
        return 80


@config_variable_registry.register
class ConfigVariableCrashReportURL(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSupport

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "crash_report_url"

    def valuespec(self):
        return HTTPUrl(
            title=_("Crash report HTTP URL"),
            help=_("By default crash reports will be sent to our crash reporting server."),
            show_as_link=False,
        )


@config_variable_registry.register
class ConfigVariableCrashReportTarget(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSupport

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "crash_report_target"

    def valuespec(self):
        return TextAscii(
            title=_("Crash report fallback mail address"),
            help=_("By default crash reports will be sent to our crash reporting server. In case "
                   "this fails for some reason, the crash reports can be sent by mail to the "
                   "address configured here."),
            size=80,
            attrencode=True,
        )


@config_variable_registry.register
class ConfigVariableSupportCredentials(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSupport

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "support_credentials"

    def valuespec(self):
        return Dictionary(
            title=_("Support credentials"),
            elements=[
                ("username", TextUnicode(
                    title=_("Username"),
                    allow_empty=False,
                )),
                ("password", PasswordFromStore(
                    title=_("Password"),
                    allow_empty=False,
                )),
            ],
            optional_keys=[],
            help=_("Set credentials for automatically submitting crash reports, "
                   "license usage reports, et al. to Tribe29. The credentials are part "
                   "of your subscription and can be found in your contract. These "
                   "credentials are also used for downloading the Checkmk software versions "
                   "from the Tribe29 website."),
        )
