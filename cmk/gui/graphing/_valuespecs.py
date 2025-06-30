#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, assert_never, Literal, TypedDict

from cmk.utils.metrics import MetricName as MetricName_

from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
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

from ._formatter import AutoPrecision, NotationFormatter, StrictPrecision, TimeFormatter
from ._from_api import metrics_from_api, RegisteredMetric
from ._graph_render_config import GraphRenderConfigBase
from ._legacy import check_metrics
from ._metrics import get_metric_spec, registered_metric_ids_and_titles
from ._translated_metrics import (
    find_matching_translation,
    lookup_metric_translations_for_check_command,
    parse_perf_data,
)
from ._unit import (
    ConvertibleUnitSpecification,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    SINotation,
    StandardScientificNotation,
    TimeNotation,
    user_specific_unit,
)


def migrate_graph_render_options_title_format(
    p: (
        Literal["plain", "add_host_name", "add_host_alias"]
        | tuple[
            Literal["add_title_infos", "plain"],
            list[Literal["add_host_name", "add_host_alias", "add_service_description"]],
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
        raise ValueError(f"invalid graph title format {p}")

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
    if isinstance(value.get("title_format"), str | tuple):
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
        ("add_service_description", _("Service name")),
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
    def __init__(
        self,
        vs_name: str,
        metric_vs_name: str,
        elements: Sequence[ValueWithUnitElement],
        validate_value_elements: ValueSpecValidateFunc[tuple[Any, ...]] | None = None,
        help: ValueSpecHelp | None = None,
    ):
        super().__init__(
            choices=[
                (
                    choice.id,
                    choice.title,
                    self._unit_vs(
                        choice.vs_type,
                        choice.symbol,
                        elements,
                        validate_value_elements,
                    ),
                )
                for choice in _sorted_unit_choices(active_config, metrics_from_api)
            ],
            help=help,
            sorted=False,
        )
        self._vs_name = vs_name
        self._metric_vs_name = metric_vs_name

    def _unit_vs(
        self,
        vs: type[Age] | type[Filesize] | type[Float] | type[Integer] | type[Percentage],
        symbol: str,
        elements: Sequence[ValueWithUnitElement],
        validate_value_elements: ValueSpecValidateFunc[tuple[Any, ...]] | None,
    ) -> Tuple:
        def set_vs(vs, title, default):
            if vs.__name__ in ["Float", "Integer"]:
                return vs(title=title, unit=symbol, default_value=default)
            return vs(title=title, default_value=default)

        return Tuple(
            elements=[set_vs(vs, elem["title"], elem["default"]) for elem in elements],
            validate=validate_value_elements,
        )

    def render_input(self, varprefix: str, value: CascadingDropdownChoiceValue) -> None:
        super().render_input(varprefix, value)
        root_prefix = varprefix[: varprefix.find(self._vs_name)]
        metric_ref_prefix = root_prefix + self._metric_vs_name
        # This will load an event listener between the unit and the metric valuespec
        html.javascript(
            f"cmk.valuespecs.update_unit_selector({json.dumps(varprefix)}, {json.dumps(metric_ref_prefix)})"
        )


@dataclass(frozen=True)
class _UnitChoice:
    id: str
    title: str
    symbol: str
    vs_type: type[Age] | type[Filesize] | type[Float] | type[Integer] | type[Percentage]

    def __hash__(self) -> int:
        return hash(self.id)


_FALLBACK_UNIT_SPEC = ConvertibleUnitSpecification(
    notation=DecimalNotation(symbol=""),
    precision=AutoPrecision(digits=2),
)


def _sorted_unit_choices(
    config: Config, registered_metrics: Mapping[str, RegisteredMetric]
) -> list[_UnitChoice]:
    return sorted(
        {
            _unit_choice_from_unit_spec(config, metric.unit_spec)
            for metric in registered_metrics.values()
        }
        | {_unit_choice_from_unit_spec(config, _FALLBACK_UNIT_SPEC)},
        key=lambda choice: choice.title,
    )


def _unit_choice_from_unit_spec(
    config: Config,
    unit_spec: ConvertibleUnitSpecification,
) -> _UnitChoice:
    unit_for_current_user = user_specific_unit(
        unit_spec,
        user,
        config,
    )
    return _UnitChoice(
        id=_id_from_unit_spec(unit_spec),
        title=_title_from_formatter(unit_for_current_user.formatter),
        symbol=unit_for_current_user.formatter.symbol,
        vs_type=_vs_type_from_formatter(unit_for_current_user.formatter),
    )


def _id_from_unit_spec(unit_spec: ConvertibleUnitSpecification) -> str:
    # Explicitly don't use eg. `unit_spec.notation.__class__.__name__` to be resilient against
    # renamings
    match unit_spec.notation:
        case DecimalNotation():
            notation_id = "DecimalNotation"
        case SINotation():
            notation_id = "SINotation"
        case IECNotation():
            notation_id = "IECNotation"
        case StandardScientificNotation():
            notation_id = "StandardScientificNotation"
        case EngineeringScientificNotation():
            notation_id = "EngineeringScientificNotation"
        case TimeNotation():
            notation_id = "TimeNotation"
    match unit_spec.precision:
        case AutoPrecision():
            precision_id = "AutoPrecision"
        case StrictPrecision():
            precision_id = "StrictPrecision"
    return f"{notation_id}_{unit_spec.notation.symbol}_{precision_id}_{unit_spec.precision.digits}"


def _title_from_formatter(formatter: NotationFormatter) -> str:
    match formatter.precision:
        case AutoPrecision(digits=digits):
            precision_title = f"auto precision, {digits} digits"
        case StrictPrecision(digits=digits):
            precision_title = f"strict precision, {digits} digits"
        case _:
            assert_never(formatter.precision)
    return " ".join(
        [
            formatter.symbol or "no symbol",
            f"({formatter.ident()}, {precision_title})",
        ]
    )


def _vs_type_from_formatter(
    formatter: NotationFormatter,
) -> type[Age] | type[Float] | type[Integer] | type[Percentage]:
    if isinstance(formatter, TimeFormatter):
        return Age
    if formatter.symbol.startswith("%"):
        return Percentage
    if formatter.precision.digits == 0:
        return Integer
    return Float


class PageVsAutocomplete(AjaxPage):
    def page(self, config: Config) -> PageResult:
        if metric_name := self.webapi_request()["metric"]:
            metric_spec = get_metric_spec(metric_name, metrics_from_api)
            unit_choice_for_metric = _unit_choice_from_unit_spec(config, metric_spec.unit_spec)
        else:
            unit_choice_for_metric = _unit_choice_from_unit_spec(config, _FALLBACK_UNIT_SPEC)

        for idx, choice in enumerate(_sorted_unit_choices(config, metrics_from_api)):
            if choice == unit_choice_for_metric:
                return {
                    "unit_choice_index": idx,
                }

        fallback_choice = _unit_choice_from_unit_spec(config, _FALLBACK_UNIT_SPEC)
        for idx, choice in enumerate(_sorted_unit_choices(config, metrics_from_api)):
            if choice == fallback_choice:
                return {
                    "unit_choice_index": idx,
                }

        raise RuntimeError("This should never happen")


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
                    for metric_id, metric_title in registered_metric_ids_and_titles(
                        metrics_from_api
                    )
                    if metric_id == value
                ),
                (value, value.title()),
            )
        ]


def _metric_choices(
    check_command: str,
    perfvars: tuple[MetricName_, ...],
    registered_metrics: Mapping[str, RegisteredMetric],
) -> Iterator[Choice]:
    for perfvar in perfvars:
        metric_name = find_matching_translation(
            MetricName_(perfvar),
            lookup_metric_translations_for_check_command(check_metrics, check_command),
        ).name
        yield (
            metric_name,
            get_metric_spec(
                metric_name,
                registered_metrics,
            ).title,
        )


def metrics_of_query(
    context: VisualContext,
    registered_metrics: Mapping[str, RegisteredMetric],
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
            row["service_perf_data"], row["service_check_command"], config=active_config
        )
        known_metrics = set([p.metric_name for p in perf_data] + row["service_metrics"])
        yield from _metric_choices(
            str(check_command),
            tuple(map(str, known_metrics)),
            registered_metrics,
        )

    if row.get("host_check_command"):
        yield from _metric_choices(
            str(row["host_check_command"]),
            tuple(map(str, row["host_metrics"])),
            registered_metrics,
        )
