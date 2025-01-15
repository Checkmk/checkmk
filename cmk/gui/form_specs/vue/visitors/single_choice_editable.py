#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence

from cmk.gui.form_specs.private.single_choice_editable import SingleChoiceEditable
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _

from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.shared_typing.configuration_entity import ConfigEntityType

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, InvalidValue
from ._utils import (
    base_i18n_form_spec,
    compute_validators,
    get_title_and_help,
)

_ParsedValueModel = str
_FrontendModel = str | None


class SingleChoiceEditableVisitor(
    FormSpecVisitor[SingleChoiceEditable, _ParsedValueModel, _FrontendModel]
):
    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if isinstance(raw_value, DefaultValue):
            return InvalidValue[_FrontendModel](reason=_("Invalid data"), fallback_value=None)
        if not isinstance(raw_value, str):
            return InvalidValue[_FrontendModel](reason=_("Invalid data"), fallback_value=None)
        return raw_value

    def _validators(self) -> Sequence[Callable[[_ParsedValueModel], object]]:
        return compute_validators(self.form_spec)

    def _to_vue(
        self, raw_value: object, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.SingleChoiceEditable, _FrontendModel]:
        # This one here requires a local import to avoid circular dependencies at import time
        from cmk.gui.watolib.configuration_entity.configuration_entity import (
            get_list_of_configuration_entities,
            get_readable_entity_selection,
        )

        title, help_text = get_title_and_help(self.form_spec)
        entity_type = ConfigEntityType(self.form_spec.entity_type.value)
        entity_selection = self.form_spec.entity_type_specifier
        entities = get_list_of_configuration_entities(entity_type, entity_selection)
        readable_entity_selection = get_readable_entity_selection(entity_type, entity_selection)
        return (
            shared_type_defs.SingleChoiceEditable(
                # FormSpec
                title=title,
                help=help_text,
                validators=build_vue_validators(self._validators()),
                # SingleChoiceEditable
                config_entity_type=self.form_spec.entity_type.value,
                config_entity_type_specifier=self.form_spec.entity_type_specifier,
                elements=[
                    shared_type_defs.SingleChoiceElement(
                        name=entity.ident, title=entity.description
                    )
                    for entity in entities
                ],
                i18n=shared_type_defs.SingleChoiceEditableI18n(
                    # TODO: remove this once we have i18n in the frontend
                    slidein_save_button=_("Save"),
                    slidein_cancel_button=_("Cancel"),
                    slidein_create_button=_("Create"),
                    slidein_new_title=_("New %s parameter") % readable_entity_selection,
                    slidein_edit_title=_("Edit %s parameter") % readable_entity_selection,
                    edit=_("Edit"),
                    create=_("Create"),
                    loading=_("Loading ..."),
                    validation_error=_("Could not validate form, errors are shown in the form"),
                    fatal_error=_("An fatal error occured:"),
                    fatal_error_reload=_("reload"),
                    no_objects=_("No options available"),
                    no_selection=_("Please select an element"),
                ),
                i18n_base=base_i18n_form_spec(),
            ),
            None if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    def _to_disk(self, raw_value: object, parsed_value: _ParsedValueModel) -> _ParsedValueModel:
        return parsed_value
