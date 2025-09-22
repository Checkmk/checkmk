#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from typing import override

from cmk.gui.form_specs.unstable.single_choice_editable import SingleChoiceEditable
from cmk.gui.i18n import _
from cmk.gui.watolib.configuration_entity.configuration_entity import (
    get_list_of_configuration_entities,
    get_readable_entity_selection,
)
from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.shared_typing.configuration_entity import ConfigEntityType

from .._type_defs import DefaultValue, IncomingData, InvalidValue
from .._utils import (
    compute_title_input_hint,
    compute_validators,
    get_prefill_default,
    get_title_and_help,
    localize,
)
from .._visitor_base import FormSpecVisitor
from ..validators import build_vue_validators

_ParsedValueModel = str | None
_FallbackModel = str | None


class SingleChoiceEditableVisitor(
    FormSpecVisitor[SingleChoiceEditable, _ParsedValueModel, _FallbackModel]
):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            fallback_value: _FallbackModel = None
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill, fallback_value),
                InvalidValue,
            ):
                return prefill_default
            value: object = prefill_default
        else:
            value = raw_value.value

        if value is None:
            return None

        if not isinstance(value, str):
            return InvalidValue[_FallbackModel](
                reason=_("Invalid data: value is not a string."), fallback_value=None
            )
        return value

    @override
    def _validators(self) -> Sequence[Callable[[_ParsedValueModel], object]]:
        def _validate_not_none(value: str | None) -> None:
            if value is None:
                raise ValidationError(
                    Message('Please choose parameters or click "Create" to add a new one.'),
                )

        validators = [_validate_not_none]

        return validators + compute_validators(self.form_spec)

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.SingleChoiceEditable, object]:
        title, help_text = get_title_and_help(self.form_spec)
        entity_type = ConfigEntityType(self.form_spec.entity_type.value)
        entity_selection = self.form_spec.entity_type_specifier
        entities = get_list_of_configuration_entities(entity_type, entity_selection)
        readable_entity_selection = get_readable_entity_selection(entity_type, entity_selection)
        input_hint = compute_title_input_hint(self.form_spec.prefill) or _(
            "Please select an element"
        )
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
                allow_editing_existing_elements=self.form_spec.allow_editing_existing_elements,
                i18n=shared_type_defs.SingleChoiceEditableI18n(
                    # TODO: remove this once we have i18n in the frontend
                    slidein_save_button=_("Save"),
                    slidein_cancel_button=_("Cancel"),
                    slidein_create_button=_("Create"),
                    slidein_new_title=_("New %s") % readable_entity_selection,
                    slidein_edit_title=_("Edit %s") % readable_entity_selection,
                    edit=_("Edit"),
                    create=localize(self.form_spec.create_element_label),
                    loading=_("Loading ..."),
                    validation_error=_("Could not validate form, errors are shown in the form"),
                    fatal_error=_("An fatal error occurred:"),
                    fatal_error_reload=_("reload"),
                    no_objects=_("No options available"),
                    no_selection=input_hint,
                    permanent_change_warning=_(
                        "Changes submitted through this form will be immediately applied to your "
                        "configuration. However, you may still need to activate them for them to take effect."
                    ),
                    permanent_change_warning_dismiss=_("Do not show again"),
                ),
            ),
            None if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> object:
        return parsed_value
