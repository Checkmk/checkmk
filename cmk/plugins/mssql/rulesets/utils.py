#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, Localizable, validators


def _migrate_alternative_to_dropdown(
    model: object,
) -> tuple[str, tuple[int | None, int | None]] | object:
    if not isinstance(model, tuple):
        return model

    if model[0] in ("no_levels", "levels"):
        return model

    if model == (None, None):
        return ("no_levels", model)

    return ("levels", model)


# TODO: migrate to form_specs.Levels after check_levels function has been implemented
def fs_mssql_backup_age(title: Localizable) -> form_specs.DictElement:
    return form_specs.DictElement(
        parameter_form=form_specs.CascadingSingleChoice(
            title=title,
            elements=[
                form_specs.CascadingSingleChoiceElement(
                    name="levels",
                    title=Localizable("Set levels"),
                    parameter_form=form_specs.Tuple(
                        title=Localizable("Set levels"),
                        elements=[
                            form_specs.TimeSpan(title=Localizable("Warning if older than")),
                            form_specs.TimeSpan(title=Localizable("Critical if older than")),
                        ],
                    ),
                ),
                form_specs.CascadingSingleChoiceElement(
                    name="no_levels",
                    title=Localizable("No levels"),
                    parameter_form=form_specs.Tuple(
                        title=Localizable("No levels"),
                        elements=[
                            form_specs.FixedValue(value=None, label=Localizable("")),
                            form_specs.FixedValue(value=None, label=Localizable("")),
                        ],
                    ),
                ),
            ],
            prefill_selection="levels",
            transform=form_specs.Migrate(model_to_form=_migrate_alternative_to_dropdown),
        )
    )


def mssql_item_spec_instance_tablespace() -> form_specs.Text:
    return form_specs.Text(
        title=Localizable("Instance & tablespace name"),
        help_text=Localizable(
            "The MSSQL instance name and the tablespace name separated by a space."
        ),
        custom_validate=validators.DisallowEmpty(),
    )
