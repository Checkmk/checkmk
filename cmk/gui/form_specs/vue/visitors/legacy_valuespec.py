#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from typing import Any

from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.private import LegacyValueSpec
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.user_errors import user_errors

from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DataOrigin, DefaultValue, InvalidValue
from ._utils import get_title_and_help

_ParsedValueModel = object
_FrontendModel = object


class LegacyValuespecVisitor(FormSpecVisitor[LegacyValueSpec, _ParsedValueModel, _FrontendModel]):
    """Visitor for LegacyValuespecs. Due to the nature of the legacy valuespecs, we can not
    directly convert them to Vue components. Instead, we need to generate the HTML code in the backend
    and pass it to the frontend. The frontend will then render the form as HTML.
    Since rendering/data/validation are mixed up in the old valuespecs, the functions here do not
    have a clear distinction
    """

    def _migrate_disk_value(self, value: object) -> object:
        try:
            return super()._migrate_disk_value(value)
        except MKUserError:
            return InvalidValue(reason=_("Unable to migrate value"), fallback_value=value)

    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        return raw_value

    def _prepare_request_context(self, value: dict[str, Any]) -> None:
        assert "input_context" in value
        for url_key, url_value in value.get("input_context", {}).items():
            request.set_var(url_key, url_value)

    def _create_input_and_readonly_html(self, varprefix: str, value: Any) -> tuple[str, str]:
        with output_funnel.plugged():
            self.form_spec.valuespec.render_input(varprefix, value)
            input_html = output_funnel.drain()

        readonly_html = self.form_spec.valuespec.value_to_html(value)
        return input_html, str(readonly_html)

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.LegacyValuespec, _FrontendModel]:
        title, help_text = get_title_and_help(self.form_spec)

        varprefix = None
        if isinstance(parsed_value, DefaultValue):
            value_to_render = self.form_spec.valuespec.default_value()
        elif self.options.data_origin == DataOrigin.FRONTEND:
            # Try to extract the value from the input_context
            # On error:   Render the form in error mode, highlighting problem fields
            # On success: Replace value with the extracted value and rendered it with a new
            #             varprefix to avoid conflicts with the previous form and stored
            #             request vars.
            assert isinstance(parsed_value, dict)
            varprefix = parsed_value.get("varprefix", "")
            with request.stashed_vars():
                self._prepare_request_context(parsed_value)

                try:
                    value_to_render = self.form_spec.valuespec.from_html_vars(varprefix)
                except MKUserError as e:
                    user_errors.add(e)
                    # Keep in mind that this default value is not used, but replaced by the
                    # previously set request vars. For more (horrible) insights see the
                    # valuespec ListOf:render_input
                    input_html, readonly_html = self._create_input_and_readonly_html(
                        varprefix, self.form_spec.valuespec.default_value()
                    )
                    return (
                        shared_type_defs.LegacyValuespec(
                            title=title,
                            help=help_text,
                            validators=[],
                            varprefix=varprefix,
                        ),
                        {"input_html": input_html, "readonly_html": readonly_html},
                    )
        else:
            value_to_render = parsed_value

        varprefix = f"legacy_varprefix_{uuid.uuid4()}" if varprefix is None else varprefix

        # Renders data from disk or data which was successfully parsed from frontend
        input_html, readonly_html = self._create_input_and_readonly_html(varprefix, value_to_render)
        return (
            shared_type_defs.LegacyValuespec(
                title=title,
                help=help_text,
                validators=[],
                varprefix=varprefix,
            ),
            {"input_html": input_html, "readonly_html": readonly_html},
        )

    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        varprefix = ""
        with output_funnel.plugged():
            try:
                if isinstance(parsed_value, DefaultValue):
                    value = self.form_spec.valuespec.default_value()
                elif self.options.data_origin == DataOrigin.FRONTEND:
                    assert isinstance(parsed_value, dict)
                    with request.stashed_vars(), output_funnel.plugged():
                        self._prepare_request_context(parsed_value)
                        varprefix = parsed_value.get("varprefix", "")
                        value = self.form_spec.valuespec.from_html_vars(varprefix)
                else:
                    value = parsed_value

                self.form_spec.valuespec.validate_datatype(value, varprefix)
                self.form_spec.valuespec.validate_value(value, varprefix)
            except MKUserError as e:
                return [
                    shared_type_defs.ValidationMessage(
                        location=[e.varname or ""], message=str(e), replacement_value=None
                    )
                ]
            finally:
                # If this funnel is not drained it will show up in the html output
                output_funnel.drain()
        return []

    def _to_disk(self, parsed_value: _ParsedValueModel) -> Any:
        if isinstance(parsed_value, DefaultValue):
            return self.form_spec.valuespec.default_value()

        if self.options.data_origin == DataOrigin.DISK:
            return self.form_spec.valuespec.transform_value(parsed_value)

        assert isinstance(parsed_value, dict)
        with request.stashed_vars():
            self._prepare_request_context(parsed_value)
            varprefix = parsed_value.get("varprefix", "")
            return self.form_spec.valuespec.from_html_vars(varprefix)
