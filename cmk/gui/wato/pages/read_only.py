#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Setup can be set into read only mode manually using this mode"""

# mypy: disable-error-code="type-arg"

import time
from collections.abc import Collection

from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.form_specs import (
    FormSpecAdapter,
    parse_data_from_field_id,
    RawDiskData,
    RawFrontendData,
    read_data_from_frontend,
    render_form_spec,
)
from cmk.gui.form_specs.generators.dict_to_catalog import create_flat_catalog_from_dictionary
from cmk.gui.form_specs.unstable import LegacyValueSpec
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.type_defs import ActionResult, PermissionName, ReadOnlySpec
from cmk.gui.userdb._user_selection import generate_wato_users_elements_function
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.valuespec import AbsoluteDate
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.utils import multisite_dir
from cmk.rulesets.internal.form_specs import (
    ListExtended,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    MultilineText,
)


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeManageReadOnly)


class _ReadOnlyFormSpecAdapter(
    FormSpecAdapter[ReadOnlySpec, TransformDataForLegacyFormatOrRecomposeFunction]
):
    def form_spec(self) -> TransformDataForLegacyFormatOrRecomposeFunction:
        return create_flat_catalog_from_dictionary(
            Dictionary(
                title=Title("Read-only mode"),
                elements={
                    "enabled": DictElement(
                        required=True,
                        parameter_form=CascadingSingleChoice(
                            title=Title("Read-only mode"),
                            prefill=DefaultValue("disabled"),
                            elements=[
                                CascadingSingleChoiceElement(
                                    name="disabled",
                                    title=Title("Disabled"),
                                    parameter_form=FixedValue(
                                        value=None,
                                        title=Title("Disabled"),
                                        label=Label("Not enabled"),
                                    ),
                                ),
                                CascadingSingleChoiceElement(
                                    name="permanent",
                                    title=Title("Enabled permanently"),
                                    parameter_form=FixedValue(
                                        value=None,
                                        title=Title("Enabled permanently"),
                                        label=Label("Enabled until disabling"),
                                    ),
                                ),
                                CascadingSingleChoiceElement(
                                    name="timerange",
                                    title=Title("Enabled in time range"),
                                    parameter_form=Tuple(
                                        title=Title("Enabled in time range"),
                                        elements=[
                                            LegacyValueSpec.wrap(
                                                AbsoluteDate(
                                                    title=_("Start"),
                                                    include_time=True,
                                                )
                                            ),
                                            LegacyValueSpec.wrap(
                                                AbsoluteDate(
                                                    title=_("Until"),
                                                    include_time=True,
                                                    default_value=time.time() + 3600,
                                                )
                                            ),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ),
                    "rw_users": DictElement(
                        required=True,
                        parameter_form=ListExtended(
                            element_template=_rw_users_choice(),
                            title=Title("Can still edit"),
                            help_text=Help("Users listed here are still allowed to modify things."),
                            editable_order=False,
                            add_element_label=Label("Add user"),
                            prefill=DefaultValue([str(user.id)]),
                        ),
                    ),
                    "message": DictElement(
                        required=True, parameter_form=MultilineText(title=Title("Message"))
                    ),
                },
            )
        )

    def from_form_spec(self, data: object) -> ReadOnlySpec:
        assert isinstance(data, dict)
        return ReadOnlySpec(
            enabled=_enabled_from_form_spec(data["enabled"]),
            rw_users=[UserId(name) for name in data["rw_users"]],
            message=data["message"],
        )

    def to_form_spec(self, model: ReadOnlySpec) -> RawDiskData:
        return RawDiskData(
            {
                "enabled": _enabled_to_form_spec(model["enabled"]),
                "rw_users": [str(name) for name in model["rw_users"]],
                "message": model["message"],
            }
        )


def _rw_users_choice() -> SingleChoiceExtended[str]:
    return SingleChoiceExtended(
        elements=[
            SingleChoiceElementExtended(name=str(user_id), title=Title("%s") % alias)
            for user_id, alias in generate_wato_users_elements_function()()
            if user_id is not None
        ],
    )


def _enabled_from_form_spec(value: object) -> bool | tuple[float, float]:
    match value:
        case ("disabled", _):
            return False
        case ("permanent", _):
            return True
        case ("timerange", (int() | float() as start, int() | float() as until)):
            return float(start), float(until)
        case _:
            raise ValueError(f"Invalid read-only mode form data: {value!r}")


def _enabled_to_form_spec(enabled: bool | tuple[float, float]) -> tuple[str, object]:
    if enabled is True:
        return "permanent", None
    if isinstance(enabled, tuple):
        return "timerange", enabled
    return "disabled", None


class ModeManageReadOnly(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "read_only"

    @classmethod
    def _vue_field_id(cls) -> str:
        return "_read_only"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["set_read_only"]

    def title(self) -> str:
        return _("Read-only mode for configuration")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Mode"), breadcrumb, form_name="read_only", button_name="_save"
        )

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        adapter = _ReadOnlyFormSpecAdapter()
        raw_settings = parse_data_from_field_id(adapter.form_spec(), self._vue_field_id())
        settings = adapter.from_form_spec(raw_settings)

        self._save(settings, pprint_value=config.wato_pprint_config)
        config.wato_read_only = settings
        flash(_("Saved read-only settings"))
        return redirect(mode_url("read_only"))

    def _save(self, settings: ReadOnlySpec, *, pprint_value: bool) -> None:
        store.save_to_mk_file(
            multisite_dir() / "read_only.mk",
            key="wato_read_only",
            value=settings,
            pprint_value=pprint_value,
        )

    def page(self, config: Config) -> None:
        html.p(
            _(
                "The Setup configuration can be set to read only mode for all users that are not "
                "permitted to ignore the read only mode. All users that are permitted to set the "
                "read only can disable it again when another permitted user enabled it before."
            )
        )

        adapter = _ReadOnlyFormSpecAdapter()

        do_validate = False
        value_for_frontend: RawDiskData | RawFrontendData
        if request.has_var(self._vue_field_id()):
            # Looks like the form has been submitted, but there were errors
            # Read the raw data from the frontend to display it again
            do_validate = True
            value_for_frontend = read_data_from_frontend(self._vue_field_id())
        else:
            value_for_frontend = adapter.to_form_spec(config.wato_read_only)

        with html.form_context("read_only", method="POST"):
            render_form_spec(
                adapter.form_spec(),
                self._vue_field_id(),
                value_for_frontend,
                do_validate,
            )
            html.hidden_fields()
