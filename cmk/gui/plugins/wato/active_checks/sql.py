#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupActiveChecks
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    NetworkPort,
    TextAreaUnicode,
    TextInput,
    Tuple,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_active_checks_sql() -> Dictionary:
    return Dictionary(
        title=_("Check SQL Database"),
        help=_(
            "This check connects to the specified database, sends a custom SQL-statement "
            "or starts a procedure, and checks that the result."
            " Please refer to the man page of the active check <tt>check_sql</tt> for details."
        ),
        optional_keys=["levels", "levels_low", "perfdata", "port", "procedure", "text", "host"],
        elements=[
            (
                "description",
                TextInput(
                    title=_("Service Description"),
                    help=_("The name of this active service to be displayed."),
                    allow_empty=False,
                ),
            ),
            (
                "dbms",
                DropdownChoice(
                    title=_("Type of Database"),
                    choices=[
                        ("mysql", _("MySQL")),
                        ("postgres", _("PostgreSQL")),
                        ("mssql", _("MSSQL")),
                        ("oracle", _("Oracle")),
                        ("db2", _("DB2")),
                        ("sqlanywhere", _("SQLAnywhere")),
                    ],
                    default_value="postgres",
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("Database Port"),
                    help=_("The port the DBMS listens to"),
                ),
            ),
            (
                "name",
                TextInput(
                    title=_("Database Name"),
                    help=_("The name of the database on the DBMS"),
                    allow_empty=False,
                ),
            ),
            (
                "user",
                TextInput(
                    title=_("Database User"),
                    help=_("The username used to connect to the database"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                MigrateToIndividualOrStoredPassword(
                    title=_("Database Password"),
                    help=_("The password used to connect to the database"),
                    allow_empty=False,
                ),
            ),
            (
                "sql",
                TextAreaUnicode(
                    title=_("Query or SQL statement"),
                    help=_(
                        "The SQL-statement or procedure name which is executed on the DBMS. It must return "
                        "a result table with one row and at least two columns. The first column must be "
                        "an integer and is interpreted as the state (0 is OK, 1 is WARN, 2 is CRIT). "
                        "Alternatively the first column can be interpreted as number value and you can "
                        "define levels for this number. The "
                        "second column is used as check output. The third column is optional and can "
                        "contain performance data."
                    ),
                    allow_empty=False,
                    monospaced=True,
                ),
            ),
            (
                "procedure",
                Dictionary(
                    optional_keys=["input"],
                    title=_("Use procedure call instead of SQL statement"),
                    help=_(
                        "If you activate this option, a name of a stored "
                        "procedure is used instead of an SQL statement. "
                        "The procedure should return one output variable, "
                        "which is evaluated in the check. If input parameters "
                        "are required, they may be specified below."
                    ),
                    elements=[
                        (
                            "useprocs",
                            FixedValue(
                                value=True,
                                totext=_("procedure call is used"),
                            ),
                        ),
                        (
                            "input",
                            TextInput(
                                title=_("Input Parameters"),
                                allow_empty=True,
                                help=_(
                                    "Input parameters, if required by the database procedure. "
                                    "If several parameters are required, use commas to separate them."
                                ),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "levels",
                Tuple(
                    title=_("Upper levels for first output item"),
                    elements=[Float(title=_("Warning at")), Float(title=_("Critical at"))],
                ),
            ),
            (
                "levels_low",
                Tuple(
                    title=_("Lower levels for first output item"),
                    elements=[Float(title=_("Warning below")), Float(title=_("Critical below"))],
                ),
            ),
            (
                "perfdata",
                TextInput(
                    title=_("Performance Data"),
                    help=_("Store output value into RRD database in a metric with this name."),
                    default_value="performance_data",
                    allow_empty=False,
                ),
            ),
            (
                "text",
                TextInput(
                    title=_("Prefix text"),
                    help=_("Additional text prefixed to the output"),
                    allow_empty=False,
                ),
            ),
            (
                "host",
                TextInput(
                    title=_("DNS hostname or IP address"),
                    help=_("This defaults to the host for which the active check is configured."),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("sql"),
        valuespec=_valuespec_active_checks_sql,
    )
)
