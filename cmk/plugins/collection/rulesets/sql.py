#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.rulesets.v1 import form_specs, Help, Label, rule_specs, Title
from cmk.rulesets.v1.form_specs import validators


def _form_active_checks_sql() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        help_text=Help(
            "This check connects to the specified database, sends a custom SQL-statement "
            "or starts a procedure, and checks that the result."
            " Please refer to the man page of the active check <tt>check_sql</tt> for details."
        ),
        elements={
            "description": form_specs.DictElement[str](
                parameter_form=form_specs.String(
                    title=Title("Service Description"),
                    help_text=Help("The name of this active service to be displayed."),
                    custom_validate=(validators.DisallowEmpty(),),
                ),
                required=True,
            ),
            "dbms": form_specs.DictElement[str](
                parameter_form=form_specs.SingleChoice(
                    title=Title("Type of Database"),
                    elements=[
                        form_specs.SingleChoiceElement("mysql", Title("MySQL")),
                        form_specs.SingleChoiceElement("postgres", Title("PostgreSQL")),
                        form_specs.SingleChoiceElement("mssql", Title("MSSQL")),
                        form_specs.SingleChoiceElement("oracle", Title("Oracle")),
                        form_specs.SingleChoiceElement("db2", Title("DB2")),
                        form_specs.SingleChoiceElement("sqlanywhere", Title("SQLAnywhere")),
                    ],
                    prefill=form_specs.DefaultValue("postgres"),
                ),
                required=True,
            ),
            "port": form_specs.DictElement[int](
                parameter_form=form_specs.Integer(
                    title=Title("Database Port"),
                    help_text=Help("The port the DBMS listens to"),
                    custom_validate=(validators.NetworkPort(),),
                ),
                required=False,
            ),
            "name": form_specs.DictElement[str](
                parameter_form=form_specs.String(
                    title=Title("Database Name"),
                    help_text=Help("The name of the database on the DBMS"),
                    custom_validate=(validators.DisallowEmpty(),),
                ),
                required=True,
            ),
            "user": form_specs.DictElement[str](
                parameter_form=form_specs.String(
                    title=Title("Database User"),
                    help_text=Help("The username used to connect to the database"),
                    custom_validate=(validators.DisallowEmpty(),),
                ),
                required=True,
            ),
            "password": form_specs.DictElement[tuple[Literal["password", "store"], str]](
                parameter_form=form_specs.Password(
                    title=Title("Database Password"),
                    help_text=Help("The password used to connect to the database"),
                ),
                required=True,
            ),
            "sql": form_specs.DictElement[str](
                parameter_form=form_specs.MultilineText(
                    title=Title("Query or SQL statement"),
                    help_text=Help(
                        "The SQL-statement or procedure name which is executed on the DBMS. It must return "
                        "a result table with one row and at least two columns. The first column must be "
                        "an integer and is interpreted as the state (0 is OK, 1 is WARN, 2 is CRIT). "
                        "Alternatively the first column can be interpreted as number value and you can "
                        "define levels for this number. The "
                        "second column is used as check output. The third column is optional and can "
                        "contain performance data."
                    ),
                    custom_validate=(validators.DisallowEmpty(),),
                    monospaced=True,
                ),
                required=True,
            ),
            "procedure": form_specs.DictElement[Mapping[str, object]](
                parameter_form=form_specs.Dictionary(
                    title=Title("Use procedure call instead of SQL statement"),
                    help_text=Help(
                        "If you activate this option, a name of a stored "
                        "procedure is used instead of an SQL statement. "
                        "The procedure should return one output variable, "
                        "which is evaluated in the check. If input parameters "
                        "are required, they may be specified below."
                    ),
                    elements={
                        "useprocs": form_specs.DictElement[bool](
                            parameter_form=form_specs.FixedValue(
                                value=True,
                                label=Label("procedure call is used"),
                            ),
                            required=True,
                        ),
                        "input": form_specs.DictElement[str](
                            parameter_form=form_specs.String(
                                title=Title("Input Parameters"),
                                help_text=Help(
                                    "Input parameters, if required by the database procedure. "
                                    "If several parameters are required, use commas to separate them."
                                ),
                            ),
                            required=False,
                        ),
                    },
                ),
                required=False,
            ),
            "levels": form_specs.DictElement[form_specs.SimpleLevelsConfigModel[float]](
                parameter_form=form_specs.SimpleLevels[float](
                    title=Title("Upper levels for first output item"),
                    level_direction=form_specs.LevelDirection.UPPER,
                    form_spec_template=form_specs.Float(),
                    prefill_fixed_levels=form_specs.InputHint((0.0, 0.0)),
                    migrate=form_specs.migrate_to_float_simple_levels,
                ),
                required=False,
            ),
            "levels_low": form_specs.DictElement[form_specs.SimpleLevelsConfigModel[float]](
                parameter_form=form_specs.SimpleLevels[float](
                    title=Title("Lower levels for first output item"),
                    level_direction=form_specs.LevelDirection.LOWER,
                    form_spec_template=form_specs.Float(),
                    prefill_fixed_levels=form_specs.InputHint((0.0, 0.0)),
                    migrate=form_specs.migrate_to_float_simple_levels,
                ),
                required=False,
            ),
            "perfdata": form_specs.DictElement[str](
                parameter_form=form_specs.String(
                    title=Title("Performance Data"),
                    help_text=Help(
                        "Store output value into RRD database in a metric with this name."
                    ),
                    prefill=form_specs.DefaultValue("performance_data"),
                    custom_validate=(validators.DisallowEmpty(),),
                ),
                required=False,
            ),
            "text": form_specs.DictElement[str](
                parameter_form=form_specs.String(
                    title=Title("Prefix text"),
                    help_text=Help("Additional text prefixed to the output"),
                    custom_validate=(validators.DisallowEmpty(),),
                ),
                required=False,
            ),
            "host": form_specs.DictElement[str](
                parameter_form=form_specs.String(
                    title=Title("DNS hostname or IP address"),
                    help_text=Help(
                        "This defaults to the host for which the active check is configured."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_sql = rule_specs.ActiveCheck(
    title=Title("Check SQL Database"),
    topic=rule_specs.Topic.DATABASES,
    name="sql",
    parameter_form=_form_active_checks_sql,
)
