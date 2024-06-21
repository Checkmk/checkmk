import uuid
from typing import Any

from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.private.definitions import LegacyValueSpec
from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import DataOrigin, DEFAULT_VALUE, Value, VisitorOptions
from cmk.gui.form_specs.vue.utils import get_title_and_help
from cmk.gui.http import request
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.user_errors import user_errors


class LegacyValuespecVisitor(FormSpecVisitor):
    """Visitor for LegacyValuespecs. Due to the nature of the legacy valuespecs, we can not
    directly convert them to Vue components. Instead, we need to generate the HTML code in the backend
    and pass it to the frontend. The frontend will then render the form as HTML.
    Since rendering/data/validation are mixed up in the old valuespecs, the functions here do not
    have a clear distinction
    """

    def __init__(self, form_spec: LegacyValueSpec, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def parse_value(self, value: Any) -> Any:
        """Only handles DataOrigin.DISK and default values.
        Data from the frontend can not be parsed at this stage, since the raw data
        (including its errors) is required in the followup functions
        """
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            # DATA_ORIGIN.DISK
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            value = self.form_spec.valuespec.default_value()

        return value

    def _prepare_request_context(self, value: dict[str, Any]) -> None:
        assert "input_context" in value
        for url_key, url_value in value.get("input_context", {}).items():
            request.set_var(url_key, url_value)

    def to_vue(self, value: Any) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = get_title_and_help(self.form_spec)
        config: dict[str, Any] = {}

        if self.options.data_origin == DataOrigin.FRONTEND:
            # Try to extract the value from the input_context
            # On error:   Render the form in error mode, highlighting problem fields
            # On success: Replace value with the extracted value and rendered it with a new
            #             varprefix to avoid conflicts with the previous form and stored
            #             request vars.
            assert isinstance(value, dict)
            varprefix = value.get("varprefix", "")
            with request.stashed_vars():
                self._prepare_request_context(value)

                try:
                    value = self.form_spec.valuespec.from_html_vars(varprefix)
                except MKUserError as e:
                    user_errors.add(e)
                    with output_funnel.plugged():
                        # Keep in mind that this default value is not used, but replaced by the
                        # previously set request vars. For more (horrible) insights see the
                        # valuespec ListOf:render_input
                        self.form_spec.valuespec.render_input(
                            varprefix, self.form_spec.valuespec.default_value()
                        )
                        return (
                            VueComponents.LegacyValuespec(
                                title=title,
                                help=help_text,
                                html=output_funnel.drain(),
                                varprefix=varprefix,
                            ),
                            None,
                        )
        else:
            varprefix = f"legacy_varprefix_{uuid.uuid4()}"

        # Renders data from disk or data which was successfully parsed from frontend
        with output_funnel.plugged():
            self.form_spec.valuespec.render_input(varprefix, value)
            return (
                VueComponents.LegacyValuespec(
                    title=title,
                    help=help_text,
                    html=output_funnel.drain(),
                    varprefix=varprefix,
                ),
                config,
            )

    def validate(self, value: Any) -> list[VueComponents.ValidationMessage]:
        with output_funnel.plugged():
            try:
                if self.options.data_origin == DataOrigin.FRONTEND:
                    assert isinstance(value, dict)
                    with request.stashed_vars(), output_funnel.plugged():
                        self._prepare_request_context(value)
                        varprefix = value.get("varprefix", "")
                        value = self.form_spec.valuespec.from_html_vars(varprefix)
                        self.form_spec.valuespec.validate_datatype(value, varprefix)
                        self.form_spec.valuespec.validate_value(value, varprefix)
                else:
                    # DataOrigin.DISK
                    self.form_spec.valuespec.render_input("", value)
            except MKUserError as e:
                return [VueComponents.ValidationMessage(location=[e.varname or ""], message=str(e))]
            finally:
                # If this funnel is not drained it will show up in the html output
                output_funnel.drain()
        return []

    def to_disk(self, value: Any) -> Any:
        assert self.options.data_origin == DataOrigin.FRONTEND
        assert isinstance(value, dict)
        with request.stashed_vars():
            self._prepare_request_context(value)
            varprefix = value.get("varprefix", "")
            return self.form_spec.valuespec.from_html_vars(varprefix)
