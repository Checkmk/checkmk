#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, Localizable, validators


def _migrate_alternative_to_dropdown(
    model: object,
) -> tuple[str, tuple[int, int] | tuple[None, None]]:
    if not isinstance(model, tuple):
        raise TypeError("Invalid type, expected tuple, got {}".format(type(model)))

    if model[0] in ("no_levels", "levels"):
        return model

    if model == (None, None):
        return ("no_levels", model)

    return ("levels", model)


# TODO: migrate to form_specs.Levels after check_levels function has been implemented
def fs_mssql_backup_age(title: Localizable) -> form_specs.composed.DictElement:
    return form_specs.composed.DictElement(
        parameter_form=form_specs.composed.CascadingSingleChoice(
            title=title,
            elements=[
                form_specs.composed.CascadingSingleChoiceElement(
                    name="levels",
                    title=Localizable("Set levels"),
                    parameter_form=form_specs.composed.TupleDoNotUseWillbeRemoved(
                        elements=[
                            form_specs.basic.TimeSpan(title=Localizable("Warning if older than")),
                            form_specs.basic.TimeSpan(title=Localizable("Critical if older than")),
                        ],
                    ),
                ),
                form_specs.composed.CascadingSingleChoiceElement(
                    name="no_levels",
                    title=Localizable("No levels"),
                    parameter_form=form_specs.composed.TupleDoNotUseWillbeRemoved(
                        elements=[
                            form_specs.basic.FixedValue(value=None, label=Localizable("")),
                            form_specs.basic.FixedValue(value=None, label=Localizable("")),
                        ],
                    ),
                ),
            ],
            prefill=form_specs.DefaultValue("levels"),
            migrate=_migrate_alternative_to_dropdown,
        )
    )


def mssql_item_spec_instance_tablespace() -> form_specs.basic.Text:
    return form_specs.basic.Text(
        title=Localizable("Instance & tablespace name"),
        help_text=Localizable(
            "The MSSQL instance name and the tablespace name separated by a space."
        ),
        custom_validate=validators.DisallowEmpty(),
    )
