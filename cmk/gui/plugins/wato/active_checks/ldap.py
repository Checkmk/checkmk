#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    Integer,
    Migrate,
    NetworkPort,
    TextInput,
    Tuple,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword, RulespecGroupActiveChecks
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_active_checks_ldap():
    return Migrate(
        migrate=lambda p: p if isinstance(p, dict) else {"name": p[0], "base_dn": p[1], **p[2]},
        valuespec=Dictionary(
            title=_("Check LDAP service access"),
            help=_(
                "This check uses <tt>check_ldap</tt> from the standard "
                "Nagios plugins in order to try the response of an LDAP "
                "server."
            ),
            optional_keys=[
                "attribute",
                "authentication",
                "port",
                "ssl",
                "hostname",
                "version",
                "response_time",
                "timeout",
            ],
            elements=[
                (
                    "name",
                    TextInput(
                        title=_("Name"),
                        help=_(
                            "The service description will be <b>LDAP</b> plus this name. If the name starts with "
                            "a caret (<tt>^</tt>), the service description will not be prefixed with <tt>LDAP</tt>."
                        ),
                        allow_empty=False,
                    ),
                ),
                (
                    "base_dn",
                    TextInput(
                        title=_("Base DN"),
                        help=_("LDAP base, e.g. ou=Development, o=Checkmk GmbH, c=de"),
                        allow_empty=False,
                        size=60,
                    ),
                ),
                (
                    "attribute",
                    TextInput(
                        title=_("Attribute to search"),
                        help=_(
                            "LDAP attribute to search, the default is <tt>(objectclass=*)</tt>."
                        ),
                        size=40,
                        allow_empty=False,
                        default_value="(objectclass=*)",
                    ),
                ),
                (
                    "authentication",
                    Tuple(
                        title=_("Authentication"),
                        elements=[
                            TextInput(
                                title=_("Bind DN"),
                                help=_("Distinguished name for binding"),
                                allow_empty=False,
                                size=60,
                            ),
                            MigrateToIndividualOrStoredPassword(
                                title=_("Password"),
                                help=_(
                                    "Password for binding, if your server requires an authentication"
                                ),
                                allow_empty=False,
                                size=20,
                            ),
                        ],
                    ),
                ),
                (
                    "port",
                    NetworkPort(
                        title=_("TCP Port"),
                        help=_(
                            "Default is 389 for normal connections and 636 for SSL connections."
                        ),
                        minvalue=1,
                        maxvalue=65535,
                        default_value=389,
                    ),
                ),
                (
                    "ssl",
                    FixedValue(
                        value=True,
                        totext=_("Use SSL"),
                        title=_("Use LDAPS (SSL)"),
                        help=_(
                            "Use LDAPS (LDAP SSLv2 method). This sets the default port number to 636"
                        ),
                    ),
                ),
                (
                    "hostname",
                    TextInput(
                        title=_("Alternative host name"),
                        help=_(
                            "Use a alternative field as host name in case of SSL Certificate Problems (eg. the Hostalias )"
                        ),
                        size=40,
                        allow_empty=False,
                        default_value="$HOSTALIAS$",
                    ),
                ),
                (
                    "version",
                    DropdownChoice(
                        title=_("LDAP Version"),
                        help=_("The default is to use version 2"),
                        choices=[
                            ("v2", _("Version 2")),
                            ("v3", _("Version 3")),
                            ("v3tls", _("Version 3 and TLS")),
                        ],
                        default_value="v2",
                    ),
                ),
                (
                    "response_time",
                    Tuple(
                        title=_("Expected response time"),
                        elements=[
                            Float(title=_("Warning if above"), unit="ms", default_value=1000.0),
                            Float(title=_("Critical if above"), unit="ms", default_value=2000.0),
                        ],
                    ),
                ),
                (
                    "timeout",
                    Integer(
                        title=_("Seconds before connection times out"),
                        unit=_("sec"),
                        default_value=10,
                    ),
                ),
            ],
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("ldap"),
        valuespec=_valuespec_active_checks_ldap,
    )
)
