#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.rulesets.v1 import form_specs, Localizable, rule_specs
from cmk.rulesets.v1.form_specs import validators


def _form_active_checks_sql() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        help_text=Localizable(
            "This check connects to the specified database, sends a custom SQL-statement "
            "or starts a procedure, and checks that the result."
            " Please refer to the man page of the active check <tt>check_sql</tt> for details."
        ),
        elements={
            "description": form_specs.DictElement[str](
                parameter_form=form_specs.Text(
                    title=Localizable("Service Description"),
                    help_text=Localizable("The name of this active service to be displayed."),
                    custom_validate=validators.DisallowEmpty(),
                ),
                required=True,
            ),
            "dbms": form_specs.DictElement[str](
                parameter_form=form_specs.SingleChoice(
                    title=Localizable("Type of Database"),
                    elements=[
                        form_specs.SingleChoiceElement("mysql", Localizable("MySQL")),
                        form_specs.SingleChoiceElement("postgres", Localizable("PostgreSQL")),
                        form_specs.SingleChoiceElement("mssql", Localizable("MSSQL")),
                        form_specs.SingleChoiceElement("oracle", Localizable("Oracle")),
                        form_specs.SingleChoiceElement("db2", Localizable("DB2")),
                        form_specs.SingleChoiceElement("sqlanywhere", Localizable("SQLAnywhere")),
                    ],
                    prefill=form_specs.DefaultValue("postgres"),
                ),
                required=True,
            ),
            "port": form_specs.DictElement[int](
                parameter_form=form_specs.Integer(
                    title=Localizable("Database Port"),
                    help_text=Localizable("The port the DBMS listens to"),
                    custom_validate=validators.NetworkPort(),
                ),
                required=False,
            ),
            "name": form_specs.DictElement[str](
                parameter_form=form_specs.Text(
                    title=Localizable("Database Name"),
                    help_text=Localizable("The name of the database on the DBMS"),
                    custom_validate=validators.DisallowEmpty(),
                ),
                required=True,
            ),
            "user": form_specs.DictElement[str](
                parameter_form=form_specs.Text(
                    title=Localizable("Database User"),
                    help_text=Localizable("The username used to connect to the database"),
                    custom_validate=validators.DisallowEmpty(),
                ),
                required=True,
            ),
            "password": form_specs.DictElement[tuple[Literal["password", "store"], str]](
                parameter_form=form_specs.Password(
                    title=Localizable("Database Password"),
                    help_text=Localizable("The password used to connect to the database"),
                ),
                required=True,
            ),
            "sql": form_specs.DictElement[str](
                parameter_form=form_specs.MultilineText(
                    title=Localizable("Query or SQL statement"),
                    help_text=Localizable(
                        "The SQL-statement or procedure name which is executed on the DBMS. It must return "
                        "a result table with one row and at least two columns. The first column must be "
                        "an integer and is interpreted as the state (0 is OK, 1 is WARN, 2 is CRIT). "
                        "Alternatively the first column can be interpreted as number value and you can "
                        "define levels for this number. The "
                        "second column is used as check output. The third column is optional and can "
                        "contain performance data."
                    ),
                    custom_validate=validators.DisallowEmpty(),
                    monospaced=True,
                ),
                required=True,
            ),
            "procedure": form_specs.DictElement[Mapping[str, object]](
                parameter_form=form_specs.Dictionary(
                    title=Localizable("Use procedure call instead of SQL statement"),
                    help_text=Localizable(
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
                                label=Localizable("procedure call is used"),
                            ),
                            required=True,
                        ),
                        "input": form_specs.DictElement[str](
                            parameter_form=form_specs.Text(
                                title=Localizable("Input Parameters"),
                                help_text=Localizable(
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
            "levels": form_specs.DictElement[form_specs.LevelsConfigModel[float]](
                parameter_form=form_specs.Levels[float](
                    title=Localizable("Upper levels for first output item"),
                    level_direction=form_specs.LevelDirection.UPPER,
                    form_spec_template=form_specs.Float(),
                    prefill_fixed_levels=form_specs.InputHint((0.0, 0.0)),
                    predictive=None,
                    migrate=form_specs.migrate_to_upper_float_levels,
                ),
                required=False,
            ),
            "levels_low": form_specs.DictElement[form_specs.LevelsConfigModel[float]](
                parameter_form=form_specs.Levels[float](
                    title=Localizable("Lower levels for first output item"),
                    level_direction=form_specs.LevelDirection.LOWER,
                    form_spec_template=form_specs.Float(),
                    prefill_fixed_levels=form_specs.InputHint((0.0, 0.0)),
                    predictive=None,
                    migrate=form_specs.migrate_to_lower_float_levels,
                ),
                required=False,
            ),
            "perfdata": form_specs.DictElement[str](
                parameter_form=form_specs.Text(
                    title=Localizable("Performance Data"),
                    help_text=Localizable(
                        "Store output value into RRD database in a metric with this name."
                    ),
                    prefill=form_specs.DefaultValue("performance_data"),
                    custom_validate=validators.DisallowEmpty(),
                ),
                required=False,
            ),
            "text": form_specs.DictElement[str](
                parameter_form=form_specs.Text(
                    title=Localizable("Prefix text"),
                    help_text=Localizable("Additional text prefixed to the output"),
                    custom_validate=validators.DisallowEmpty(),
                ),
                required=False,
            ),
            "host": form_specs.DictElement[str](
                parameter_form=form_specs.Text(
                    title=Localizable("DNS hostname or IP address"),
                    help_text=Localizable(
                        "This defaults to the host for which the active check is configured."
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_sql = rule_specs.ActiveCheck(
    title=Localizable("Check SQL Database"),
    topic=rule_specs.Topic.DATABASES,
    eval_type=rule_specs.EvalType.ALL,
    name="sql",
    parameter_form=_form_active_checks_sql,
)
