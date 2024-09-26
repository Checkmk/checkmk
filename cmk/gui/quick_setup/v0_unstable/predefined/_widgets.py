#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.fields.definitions import HOST_NAME_REGEXP
from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.form_specs.vue.shared_type_defs import DictionaryLayout
from cmk.gui.quick_setup.v0_unstable.definitions import UniqueBundleIDStr, UniqueFormSpecIDStr
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, FormSpecWrapper
from cmk.gui.watolib.configuration_bundles import ConfigBundleStore
from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.rulesets.v1 import Message, Title
from cmk.rulesets.v1.form_specs import DictElement, FieldSize, String, validators
from cmk.rulesets.v1.form_specs._base import DefaultValue


def unique_id_formspec_wrapper(
    title: Title,
    prefill_template: str = "unique_id",
) -> FormSpecWrapper:
    return FormSpecWrapper(
        id=FormSpecId(UniqueFormSpecIDStr),
        form_spec=DictionaryExtended(
            elements={
                UniqueBundleIDStr: DictElement(
                    parameter_form=String(
                        title=title,
                        field_size=FieldSize.MEDIUM,
                        custom_validate=(
                            validators.LengthInRange(
                                min_value=1,
                                error_msg=Message("%s cannot be empty") % str(title),
                            ),
                        ),
                        prefill=DefaultValue(
                            unique_default_name_suggestion(
                                template=prefill_template,
                                used_names=list(ConfigBundleStore().load_for_reading().keys()),
                            )
                        ),
                    ),
                    required=True,
                )
            },
            layout=DictionaryLayout.two_columns,
        ),
    )


def _host_name_dict_element(
    title: Title = Title("Host name"),
    prefill_template: str = "qs_host",
) -> DictElement:
    return DictElement(
        parameter_form=String(
            title=title,
            field_size=FieldSize.MEDIUM,
            custom_validate=(
                validators.LengthInRange(
                    min_value=1,
                    error_msg=Message("%s cannot be empty") % str(title),
                ),
                validators.MatchRegex(HOST_NAME_REGEXP),
            ),
            prefill=DefaultValue(
                unique_default_name_suggestion(
                    template=prefill_template,
                    used_names=set(folder_tree().root_folder().all_hosts_recursively()),
                )
            ),
        ),
        required=True,
    )


FOLDER_PATTERN = (
    r"^(?:[~\\\/]?[-_ a-zA-Z0-9.]{1,32}(?:[~\\\/][-_ a-zA-Z0-9.]{1,32})*[~\\\/]?|[~\\\/]?)$"
)


def _host_path_dict_element(title: Title = Title("Host Path")) -> DictElement:
    return DictElement(
        parameter_form=String(
            title=title,
            field_size=FieldSize.MEDIUM,
            custom_validate=(validators.MatchRegex(FOLDER_PATTERN),),
        ),
        required=True,
    )


def host_name_and_host_path_formspec_wrapper(
    host_prefill_template: str = "qs_host",
) -> FormSpecWrapper:
    return FormSpecWrapper(
        id=FormSpecId("host_data"),
        form_spec=DictionaryExtended(
            elements={
                "host_name": _host_name_dict_element(prefill_template=host_prefill_template),
                "host_path": _host_path_dict_element(),
            },
            layout=DictionaryLayout.two_columns,
        ),
    )
