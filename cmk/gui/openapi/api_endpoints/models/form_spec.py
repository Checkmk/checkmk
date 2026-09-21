#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Self

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.shared_typing import vue_formspec_components as shared_type_defs


@api_model
class FormSpecValidationMessageModel:
    location: list[str] = api_field(
        description="Path to the rejected element, empty for the whole form spec.",
        example=["levels", "1"],
    )
    message: str = api_field(
        description="Reason the validation failed.",
        example="The value must be at least 0.",
    )
    replacement_value: object = api_field(
        description="Value to display in the frontend instead of the one that failed validation.",
        example=0,
    )


@api_model
class FormSpecValidationErrorsModel:
    validation_errors: list[FormSpecValidationMessageModel] = api_field(
        description="Validation errors",
    )

    @classmethod
    def from_messages(cls, messages: Sequence[shared_type_defs.ValidationMessage]) -> Self:
        return cls(
            validation_errors=[
                FormSpecValidationMessageModel(
                    location=list(message.location),
                    message=message.message,
                    replacement_value=message.replacement_value,
                )
                for message in messages
            ]
        )
