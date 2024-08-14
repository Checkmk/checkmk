#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.quick_setup.v0_unstable.definitions import UniqueBundleIDStr, UniqueFormSpecIDStr
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecDictWrapper, FormSpecId
from cmk.gui.watolib.configuration_bundles import ConfigBundleStore

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String, validators
from cmk.rulesets.v1.form_specs._base import DefaultValue


def unique_id_formspec_wrapper(
    title: Title,
    prefill_template: str = "unique_id",
) -> FormSpecDictWrapper:
    return FormSpecDictWrapper(
        id=FormSpecId(UniqueFormSpecIDStr),
        rendering_option="table",
        form_spec=Dictionary(
            elements={
                UniqueBundleIDStr: DictElement(
                    parameter_form=String(
                        title=title,
                        field_size=FieldSize.MEDIUM,
                        custom_validate=(validators.LengthInRange(min_value=1),),
                        prefill=DefaultValue(
                            unique_default_name_suggestion(
                                template=prefill_template,
                                used_names=list(ConfigBundleStore().load_for_reading().keys()),
                            )
                        ),
                    ),
                    required=True,
                )
            }
        ),
    )
