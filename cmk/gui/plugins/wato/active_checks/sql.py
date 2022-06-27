#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Union

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupActiveChecks
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    Integer,
    TextAreaUnicode,
    TextInput,
    Transform,
    Tuple,
)


def transform_check_sql_perfdata(perfdata: Union[str, bool]) -> str:
    if isinstance(perfdata, str):
        return perfdata
    return "performance_data"


def _valuespec_active_checks_sql() -> Dictionary:
    return Dictionary(
        title=_("Check SQL Database"),
        help=_(
            "This check connects to the specified database, sends a custom SQL-statement "
            "or starts a procedure, and checks that the result has a defined format "
            "containing three columns, a number, a text, and performance data. Upper or "
            "lower levels may be defined here.  If they are not defined the number is taken "
            "as the state of the check.  If a procedure is used, input parameters of the "
            "procedures may by given as comma separated list. "
            "This check uses the active check <tt>check_sql</tt>."
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
                    ],
                    default_value="postgres",
                ),
            ),
            (
                "port",
                Integer(
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
                IndividualOrStoredPassword(
                    title=_("Database Password"),
                    help=_("The password used to connect to the database"),
                    allow_empty=False,
                ),
            ),
            (
                "sql",
                Transform(
                    valuespec=TextAreaUnicode(
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
                    # Former Alternative(Text, Alternative(FileUpload, Text)) based implementation
                    # would save a string or a tuple with a string or a binary array as third element
                    # which would then be turned into a string.
                    # Just make all this a string
                    forth=lambda old_val: [
                        elem.decode() if isinstance(elem, bytes) else str(elem)
                        for elem in ((old_val[-1] if isinstance(old_val, tuple) else old_val),)
                    ][0],
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
                Transform(
                    TextInput(
                        title=_("Performance Data"),
                        help=_("Store output value into RRD database in a metric with this name."),
                        default_value="performance_data",
                        allow_empty=False,
                    ),
                    forth=transform_check_sql_perfdata,
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
        name="active_checks:sql",
        valuespec=_valuespec_active_checks_sql,
    )
)
