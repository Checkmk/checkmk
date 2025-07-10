#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pprint
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from typing import TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.log import logger

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._registry import get_visitor
from ._type_defs import DEFAULT_VALUE, FormSpecValidationError, IncomingData, RawFrontendData

T = TypeVar("T")


class DisplayMode(Enum):
    EDIT = "edit"
    READONLY = "readonly"
    BOTH = "both"


class RenderMode(Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    BACKEND_AND_FRONTEND = "backend_and_frontend"


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    spec: shared_type_defs.FormSpec
    data: object
    validation: list[shared_type_defs.ValidationMessage]
    display_mode: str


def _process_validation_errors(
    validation_errors: list[shared_type_defs.ValidationMessage],
) -> None:
    """This functions introduces validation errors from the vue-world into the CheckMK-GUI-world
    The CheckMK-GUI works with a global parameter user_errors.
    These user_errors include the field_id of the broken input field and the error text
    """
    # TODO: this function will become obsolete once all errors are shown within the form spec
    #       and valuespecs render_input no longer relies on the varprefixes in user_errors
    if not validation_errors:
        return

    first_error = validation_errors[0]
    raise MKUserError(
        "" if not first_error.location else first_error.location[-1],
        _("Cannot save the form because it contains errors."),
    )


def process_validation_messages(
    validation_messages: list[shared_type_defs.ValidationMessage],
) -> None:
    """Helper function to process validation errors in general use cases.

    Args:
        validation_messages: Validation messages returned by Visitor.validate

    Raises:
        FormSpecValidationError: An error storing the validation messages
    """
    if validation_messages:
        raise FormSpecValidationError(validation_messages)


def render_form_spec(
    form_spec: FormSpec[T],
    field_id: str,
    value: IncomingData,
    do_validate: bool,
    display_mode: DisplayMode = DisplayMode.EDIT,
) -> None:
    """Renders the valuespec via vue within a div"""
    vue_app_config = serialize_data_for_frontend(
        form_spec, field_id, do_validate, value, display_mode
    )
    if active_config.load_frontend_vue == "inject":
        logger.warning(
            "Vue app config:\n%s", pprint.pformat(asdict(vue_app_config), width=220, indent=2)
        )
        logger.warning("Vue value:\n%s", pprint.pformat(vue_app_config.data, width=220))
        logger.warning("Vue validation:\n%s", pprint.pformat(vue_app_config.validation, width=220))
    html.vue_component(component_name="cmk-form-spec", data=asdict(vue_app_config))


def parse_data_from_frontend(form_spec: FormSpec[T], field_id: str) -> object:
    """Computes/validates the value from a vue formular field"""
    if not request.has_var(field_id):
        raise MKGeneralException("Formular data is missing in request")
    value_from_frontend = RawFrontendData(json.loads(request.get_str_input_mandatory(field_id)))
    visitor = get_visitor(form_spec)
    _process_validation_errors(visitor.validate(value_from_frontend))
    return visitor.to_disk(value_from_frontend)


def validate_value_from_frontend(
    form_spec: FormSpec[T], value: IncomingData
) -> Sequence[shared_type_defs.ValidationMessage]:
    visitor = get_visitor(form_spec)
    return visitor.validate(value)


def serialize_data_for_frontend(
    form_spec: FormSpec[T],
    field_id: str,
    do_validate: bool,
    value: IncomingData = DEFAULT_VALUE,
    display_mode: DisplayMode = DisplayMode.EDIT,
) -> VueAppConfig:
    """Serializes backend value to vue app compatible config."""
    visitor = get_visitor(form_spec)
    vue_component, vue_value = visitor.to_vue(value)

    validation: list[shared_type_defs.ValidationMessage] = []
    if do_validate:
        validation = visitor.validate(value)

    return VueAppConfig(
        id=field_id,
        spec=vue_component,
        data=vue_value,
        validation=validation,
        display_mode=display_mode.value,
    )
