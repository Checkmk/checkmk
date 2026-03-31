#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Hostname,
    NetworkPort,
    TextInput,
    TextUnicode,
    UploadOrPasteTextFile,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_no_auth() -> FixedValue[bool]:
    return FixedValue(
        value=True,
        title=_("Deploy mk_mongodb.py without authentication."),
        totext=_("Deploy without authentication."),
    )


def _valuespec_auth() -> Dictionary:
    return Dictionary(
        title=_("Deploy mk_mongodb.py with authentication."),
        required_keys=["username", "password", "auth_mechanism", "auth_source"],
        elements=[
            (
                "auth_mechanism",
                DropdownChoice(
                    title=_("Authentication mechanism"),
                    choices=[
                        ("DEFAULT", _("Auto (DEFAULT)")),
                        ("MONGODB-X509", _("MongoDB >= 5.0 (MONGODB-X509)")),
                        ("SCRAM-SHA-256", _("MongoDB >= 4.0 (SCRAM-SHA-256)")),
                        ("SCRAM-SHA-1", _("MongoDB >= 3.0 (SCRAM-SHA-1)")),
                        ("MONGODB-CR", _("MongoDB < 3.0 (MONGODB-CR)")),
                    ],
                    default_value="DEFAULT",
                ),
            ),
            (
                "host",
                Hostname(
                    title=_("Host name"),
                    default_value="localhost",
                    help=_("The host name of the MongoDB server."),
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("Port"),
                    default_value=27017,
                ),
            ),
            (
                "tls",
                Dictionary(
                    required_keys=["insecure"],
                    title=_("Enable TLS"),
                    elements=[
                        (
                            "insecure",
                            DropdownChoice(
                                title=_("Verify certificates"),
                                choices=[
                                    (True, _("Ignore certificate errors (insecure)")),
                                    (False, _("Verify Certificates")),
                                ],
                                default_value=False,
                            ),
                        ),
                        (
                            "ca_file",
                            TextUnicode(
                                title=_("Path to CA File"),
                                help=_(
                                    "Has to contain a single or a bundle "
                                    "of 'certification authority' certificates."
                                ),
                            ),
                        ),
                        (
                            "cert_key_file",
                            CascadingDropdown(
                                title=_("Certificate Key File"),
                                choices=[
                                    (
                                        "uploaded_cert_file",
                                        _("Upload Certificate key file"),
                                        UploadOrPasteTextFile(
                                            elements=[],
                                            title=_("Import"),
                                            file_title=_("PEM File"),
                                            mime_types=[
                                                "application/x-x509-user-cert",
                                                "application/x-x509-ca-cert",
                                                "application/pkix-cert",
                                            ],
                                            allowed_extensions=[".pem", ".crt"],
                                        ),
                                    ),
                                    (
                                        "cert_filepath",
                                        _("Path to Certificate key file"),
                                        TextInput(
                                            title=_("Path to Cert Key file"),
                                            help=_("Has to contain the path to the Cert Key File."),
                                        ),
                                    ),
                                ],
                                help=_(
                                    "This is required only if the authentication method is MONGODB-X509"
                                ),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth_source",
                TextUnicode(
                    title=_("Authentication source"),
                    default_value="admin",
                    help=_("The database to authenticate on."),
                    allow_empty=False,
                ),
            ),
            (
                "username",
                TextUnicode(
                    title=_("Username"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                MigrateToIndividualOrStoredPassword(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
        ],
    )


def _valuespec_no_deploy() -> FixedValue[None]:
    return FixedValue(
        value=None,
        title=_("Do not deploy mk_mongodb.py plug-in"),
        totext=_("Do not deploy."),
    )


def _valuespec_agent_config_mk_mongodb() -> Alternative:
    return Alternative(
        title=_("MongoDB (Linux)"),
        help=_("This will deploy the agent plug-in <tt>mk_mongodb.py</tt>."),
        elements=[
            _valuespec_no_auth(),
            _valuespec_auth(),
            _valuespec_no_deploy(),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_mongodb"),
        valuespec=_valuespec_agent_config_mk_mongodb,
    )
)
