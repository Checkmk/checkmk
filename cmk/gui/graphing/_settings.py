#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.gui.form_specs.generators.age import Age
from cmk.gui.watolib.config_domain_name import ConfigVariable, GlobalSettingsContext
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupUserInterface
from cmk.rulesets.internal.form_specs import ListExtended
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Message, Title


def _form_spec(context: GlobalSettingsContext) -> ListExtended[Mapping[str, object]]:
    return ListExtended(
        element_template=fs.Dictionary(
            elements={
                "title": fs.DictElement(
                    required=True,
                    parameter_form=fs.String(
                        title=Title("Title"),
                        custom_validate=[fs.validators.LengthInRange(min_value=1)],
                    ),
                ),
                "duration": fs.DictElement(
                    required=True,
                    parameter_form=Age(title=Title("Duration")),
                ),
            },
        ),
        title=Title("Custom graph time ranges"),
        prefill=fs.DefaultValue(
            [dict(graph_range) for graph_range in context.configured_graph_timeranges]
        ),
        custom_validate=[
            fs.validators.LengthInRange(
                min_value=1,
                error_msg=Message("Please specify at least one graph time range."),
            )
        ],
    )


ConfigVariableGraphTimeranges = ConfigVariable(
    group=ConfigVariableGroupUserInterface,
    primary_domain=ConfigDomainGUI,
    ident="graph_timeranges",
    form_spec=_form_spec,
)
