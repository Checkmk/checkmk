#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import cmk.utils.regex

from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.fields.definitions import HOST_NAME_REGEXP
from cmk.gui.form_specs.generators.folder import create_full_path_folder_choice
from cmk.gui.form_specs.private.two_column_dictionary import TwoColumnDictionary
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.quick_setup.v0_unstable.definitions import (
    QSHostName,
    QSHostPath,
    QSSiteSelection,
    UniqueBundleIDStr,
    UniqueFormSpecIDStr,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, FormSpecWrapper
from cmk.gui.user_sites import get_configured_site_choices, site_attribute_default_value
from cmk.gui.watolib.configuration_bundle_store import ConfigBundleStore
from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    FieldSize,
    InputHint,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)

ID_VALIDATION_REGEX = cmk.utils.regex.regex(cmk.utils.regex.REGEX_ID, re.ASCII)


def unique_id_formspec_wrapper(
    title: Title,
    prefill_template: str = "unique_id",
) -> FormSpecWrapper:
    return FormSpecWrapper(
        id=FormSpecId(UniqueFormSpecIDStr),
        form_spec=TwoColumnDictionary(
            elements={
                UniqueBundleIDStr: DictElement(
                    parameter_form=String(
                        title=title,
                        field_size=FieldSize.MEDIUM,
                        custom_validate=(
                            validators.LengthInRange(
                                min_value=1,
                                error_msg=Message("%s is required but not specified.")
                                % title.localize(translate_to_current_language),
                            ),
                            validators.MatchRegex(
                                regex=ID_VALIDATION_REGEX,
                                error_msg=Message(
                                    "An identifier must only consist of letters, digits, dash and underscore and it must start with a letter or underscore."
                                ),
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
        ),
    )


def _host_name_dict_element(
    title: Title = Title("Host name"),
    prefill_template: str = "qs_host",
) -> DictElement:
    title_str: str = title.localize(translate_to_current_language).lower()
    return DictElement(
        parameter_form=String(
            title=title,
            field_size=FieldSize.MEDIUM,
            custom_validate=(
                validators.LengthInRange(
                    min_value=1,
                    max_value=240,
                    error_msg=Message(
                        "The %s is required but not specified or too long. Please enter a name that is not yet in use and is no longer than 253 characters."
                    )
                    % title_str,
                ),
                validators.MatchRegex(
                    regex=HOST_NAME_REGEXP,
                    error_msg=Message(
                        "Found invalid characters in the %s. Please ensure that only letters from the English alphabet, numbers and the special characters dot, hyphen and underscore are used."
                    )
                    % title_str,
                ),
            ),
            prefill=DefaultValue(
                unique_default_name_suggestion(
                    template=prefill_template,
                    used_names=set(folder_tree().root_folder().all_hosts_recursively()),
                )
            ),
            help_text=Help(
                "Specify the name of your host where all the services will be located. "
                "The host name must be unique."
            ),
        ),
        required=True,
    )


def _host_path_dict_element(title: Title = Title("Folder")) -> DictElement:
    return DictElement(
        parameter_form=create_full_path_folder_choice(
            title=title,
            help_text=Help("Specify the location where the host will be created."),
            allow_new_folder_creation=True,
        ),
        required=True,
    )


def host_name_and_host_path_formspec_wrapper(
    host_prefill_template: str = "qs_host",
) -> FormSpecWrapper:
    return FormSpecWrapper(
        id=FormSpecId("host_data"),
        form_spec=TwoColumnDictionary(
            elements={
                QSHostName: _host_name_dict_element(prefill_template=host_prefill_template),
                QSHostPath: _host_path_dict_element(),
            },
        ),
    )


def site_formspec_wrapper() -> FormSpecWrapper:
    site_default_value = site_attribute_default_value()
    return FormSpecWrapper(
        id=FormSpecId("site"),
        form_spec=TwoColumnDictionary(
            elements={
                QSSiteSelection: DictElement(
                    parameter_form=SingleChoice(
                        elements=[
                            SingleChoiceElement(
                                name=site_id,
                                title=Title(  # pylint: disable=localization-of-non-literal-string
                                    title
                                ),
                            )
                            for site_id, title in get_configured_site_choices()
                        ],
                        title=Title("Site selection"),
                        prefill=(
                            DefaultValue(site_default_value)
                            if site_default_value
                            else InputHint(Title("Please choose"))
                        ),
                    ),
                    required=True,
                )
            },
        ),
    )
