#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Literal

from typing_extensions import TypedDict

from cmk.utils.metrics import MetricName as MetricName_

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.type_defs import Choice, Choices, GraphTitleFormatVS, VisualContext
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    CascadingDropdownChoiceValue,
    Checkbox,
    Dictionary,
    DropdownChoice,
    DropdownChoiceWithHostAndServiceHints,
    Filesize,
    Float,
    Fontsize,
    Integer,
    ListChoice,
    MigrateNotUpdated,
    Percentage,
    Tuple,
    ValueSpecHelp,
    ValueSpecValidateFunc,
)
from cmk.gui.visuals import livestatus_query_bare

from ._graph_render_config import GraphRenderConfigBase
from ._loader import registered_units
from ._utils import (
    get_extended_metric_info,
    parse_perf_data,
    perfvar_translation,
    registered_metrics,
)


def migrate_graph_render_options_title_format(
    p: (
        Literal["plain"]
        | Literal["add_host_name"]
        | Literal["add_host_alias"]
        | tuple[
            Literal["add_title_infos"],
            list[
                Literal["add_host_name"]
                | Literal["add_host_alias"]
                | Literal["add_service_description"]
            ],
        ]
        | Sequence[GraphTitleFormatVS]
    ),
) -> Sequence[GraphTitleFormatVS]:
    # ->1.5.0i2 pnp_graph reportlet
    if p == "add_host_name":
        return ["plain", "add_host_name"]
    if p == "add_host_alias":
        return ["plain", "add_host_alias"]

    #   1.5.0i2->2.0.0i1 title format DropdownChoice to ListChoice
    if p == "plain":
        return ["plain"]

    if isinstance(p, tuple):
        if p[0] == "add_title_infos":
            infos: Sequence[GraphTitleFormatVS] = ["plain"] + p[1]
            return infos
        if p[0] == "plain":
            return ["plain"]

    # Because the spec could come from a JSON request CMK-6339
    if isinstance(p, list) and len(p) == 2 and p[0] == "add_title_infos":
        return ["plain"] + p[1]

    return p


def migrate_graph_render_options(value):
    # Graphs in painters and dashlets had the show_service option before 1.5.0i2.
    # This has been consolidated with the option title_format from the reportlet.
    if value.pop("show_service", False):
        value["title_format"] = ["plain", "add_host_name", "add_service_description"]
    #   1.5.0i2->2.0.0i1 title format DropdownChoice to ListChoice
    if isinstance(value.get("title_format"), (str, tuple)):
        value["title_format"] = migrate_graph_render_options_title_format(value["title_format"])
    return value


def vs_graph_render_options(default_values=None, exclude=None):
    return MigrateNotUpdated(
        valuespec=Dictionary(
            elements=vs_graph_render_option_elements(default_values, exclude),
            optional_keys=[],
            title=_("Graph rendering options"),
        ),
        migrate=migrate_graph_render_options,
    )


def _vs_title_infos() -> ListChoice:
    choices = [
        ("plain", _("Graph title")),
        ("add_host_name", _("Host name")),
        ("add_host_alias", _("Host alias")),
        ("add_service_description", _("Service description")),
    ]
    return ListChoice(title=_("Title format"), choices=choices, default_value=["plain"])


def vs_graph_render_option_elements(default_values=None, exclude=None):
    # Allow custom default values to be specified by the caller. This is, for example,
    # needed by the dashlets which should add the host/service by default.
    default_values = GraphRenderConfigBase.model_validate(default_values or {})

    elements = [
        (
            "font_size",
            Fontsize(
                default_value=default_values.font_size,
            ),
        ),
        (
            "show_title",
            DropdownChoice(
                title=_("Title"),
                choices=[
                    (False, _("Don't show graph title")),
                    (True, _("Show graph title")),
                    ("inline", _("Show graph title on graph area")),
                ],
                default_value=default_values.show_title,
            ),
        ),
        (
            "title_format",
            MigrateNotUpdated(
                valuespec=_vs_title_infos(),
                migrate=migrate_graph_render_options_title_format,
            ),
        ),
        (
            "show_graph_time",
            Checkbox(
                title=_("Show graph time range"),
                label=_("Show the graph time range on top of the graph"),
                default_value=default_values.show_graph_time,
            ),
        ),
        (
            "show_margin",
            Checkbox(
                title=_("Show margin round the graph"),
                label=_("Show a margin round the graph"),
                default_value=default_values.show_margin,
            ),
        ),
        (
            "show_legend",
            Checkbox(
                title=_("Show legend"),
                label=_("Show the graph legend"),
                default_value=default_values.show_legend,
            ),
        ),
        (
            "show_vertical_axis",
            Checkbox(
                title=_("Show vertical axis"),
                label=_("Show the graph vertical axis"),
                default_value=default_values.show_vertical_axis,
            ),
        ),
        (
            "vertical_axis_width",
            CascadingDropdown(
                title=_("Vertical axis width"),
                orientation="horizontal",
                choices=[
                    ("fixed", _("Use fixed width (relative to font size)")),
                    (
                        "explicit",
                        _("Use absolute width:"),
                        Float(title="", default_value=40.0, unit=_("pt")),
                    ),
                ],
            ),
        ),
        (
            "show_time_axis",
            Checkbox(
                title=_("Show time axis"),
                label=_("Show the graph time axis"),
                default_value=default_values.show_time_axis,
            ),
        ),
        (
            "show_controls",
            Checkbox(
                title=_("Show controls"),
                label=_("Show the graph controls"),
                default_value=default_values.show_controls,
            ),
        ),
        (
            "show_pin",
            Checkbox(
                title=_("Show pin"),
                label=_("Show the pin"),
                default_value=default_values.show_pin,
            ),
        ),
        (
            "show_time_range_previews",
            Checkbox(
                title=_("Show time range previews"),
                label="Show previews",
                default_value=default_values.show_time_range_previews,
            ),
        ),
        (
            "fixed_timerange",
            Checkbox(
                title=_("Time range synchronization"),
                label="Do not follow timerange changes of other graphs on the current page",
                default_value=default_values.fixed_timerange,
            ),
        ),
    ]

    if exclude:
        elements = [x for x in elements if x[0] not in exclude]

    return elements


class ValueWithUnitElement(TypedDict):
    title: str
    default: float


class ValuesWithUnits(CascadingDropdown):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        vs_name: str,
        metric_vs_name: str,
        elements: list[ValueWithUnitElement],
        validate_value_elemets: ValueSpecValidateFunc[tuple[Any, ...]] | None = None,
        help: ValueSpecHelp | None = None,
    ):
        super().__init__(choices=self._unit_choices, help=help)
        self._vs_name = vs_name
        self._metric_vs_name = metric_vs_name
        self._elements = elements
        self._validate_value_elements = validate_value_elemets

    def _unit_vs(
        self,
        vs: type[Age] | type[Filesize] | type[Float] | type[Integer] | type[Percentage],
        symbol: str,
    ) -> Tuple:
        def set_vs(vs, title, default):
            if vs.__name__ in ["Float", "Integer"]:
                return vs(title=title, unit=symbol, default_value=default)
            return vs(title=title, default_value=default)

        return Tuple(
            elements=[set_vs(vs, elem["title"], elem["default"]) for elem in self._elements],
            validate=self._validate_value_elements,
        )

    def _unit_choices(self) -> Sequence[tuple[str, str, Tuple]]:
        return [
            (
                registered_unit.name,
                registered_unit.description or registered_unit.title,
                self._unit_vs(registered_unit.valuespec, registered_unit.symbol),
            )
            for registered_unit in registered_units()
        ]

    @staticmethod
    def resolve_units(metric_name: MetricName_ | None) -> PageResult:
        # This relies on python3.8 dictionaries being always ordered
        # Otherwise it is not possible to mach the unit name to value
        # CascadingDropdowns enumerate the options instead of using keys
        if metric_name:
            required_unit = get_extended_metric_info(metric_name)["unit"]["id"]
        else:
            required_unit = ""

        known_units = [registered_unit.name for registered_unit in registered_units()]
        try:
            index = known_units.index(required_unit)
        except ValueError:
            index = known_units.index("")

        return {"unit": required_unit, "option_place": index}

    def render_input(self, varprefix: str, value: CascadingDropdownChoiceValue) -> None:
        super().render_input(varprefix, value)
        root_prefix = varprefix[: varprefix.find(self._vs_name)]
        metric_ref_prefix = root_prefix + self._metric_vs_name
        # This will load an event listener between the unit and the metric valuespec
        html.javascript(
            f"cmk.valuespecs.update_unit_selector({json.dumps(varprefix)}, {json.dumps(metric_ref_prefix)})"
        )


class PageVsAutocomplete(AjaxPage):
    def page(self) -> PageResult:
        return ValuesWithUnits.resolve_units(self.webapi_request()["metric"])


class MetricName(DropdownChoiceWithHostAndServiceHints):
    """Factory of a Dropdown menu from all known metric names"""

    ident = "monitored_metrics"

    def __init__(self, **kwargs: Any) -> None:
        # Customer's metrics from local checks or other custom plug-ins will now appear as metric
        # options extending the registered metric names on the system. Thus assuming the user
        # only selects from available options we skip the input validation(invalid_choice=None)
        # Since it is not possible anymore on the backend to collect the host & service hints
        kwargs_with_defaults: Mapping[str, Any] = {
            "css_spec": ["ajax-vals"],
            "hint_label": _("metric"),
            "title": _("Metric"),
            "regex": re.compile("^[a-zA-Z0-9][a-zA-Z0-9_]*$"),
            "regex_error": _(
                "Metric names must only consist of letters, digits and "
                "underscores and they must start with a letter or digit."
            ),
            "autocompleter": ContextAutocompleterConfig(
                ident=self.ident,
                show_independent_of_context=True,
                dynamic_params_callback_name="host_and_service_hinted_autocompleter",
            ),
            **kwargs,
        }
        super().__init__(**kwargs_with_defaults)

    def _validate_value(self, value: str | None, varprefix: str) -> None:
        if value == "":
            raise MKUserError(varprefix, self._regex_error)
        # dropdown allows empty values by default
        super()._validate_value(value, varprefix)

    def _choices_from_value(self, value: str | None) -> Choices:
        if value is None:
            return list(self.choices())
        # Need to create an on the fly metric option
        return [
            next(
                (
                    (metric_id, metric_title)
                    for metric_id, metric_title in registered_metrics()
                    if metric_id == value
                ),
                (value, value.title()),
            )
        ]


def _metric_choices(check_command: str, perfvars: tuple[MetricName_, ...]) -> Iterator[Choice]:
    for perfvar in perfvars:
        metric_name = perfvar_translation(perfvar, check_command)["name"]
        yield metric_name, str(get_extended_metric_info(metric_name)["title"])


def metrics_of_query(
    context: VisualContext,
) -> Iterator[Choice]:
    # Fetch host data with the *same* query. This saves one round trip. And head
    # host has at least one service
    columns = [
        "service_description",
        "service_check_command",
        "service_perf_data",
        "service_metrics",
        "host_check_command",
        "host_metrics",
    ]

    row = {}
    for row in livestatus_query_bare("service", context, columns):
        perf_data, check_command = parse_perf_data(
            row["service_perf_data"], row["service_check_command"]
        )
        known_metrics = set([p.metric_name for p in perf_data] + row["service_metrics"])
        yield from _metric_choices(str(check_command), tuple(map(str, known_metrics)))

    if row.get("host_check_command"):
        yield from _metric_choices(
            str(row["host_check_command"]), tuple(map(str, row["host_metrics"]))
        )
