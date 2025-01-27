#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import sys
import traceback
from collections.abc import Iterator, Sequence
from itertools import chain

from livestatus import LivestatusTestingError

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.type_defs import FilterHTTPVariables, SingleInfos, VisualContext
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.valuespec import (
    ABCPageListOfMultipleGetChoice,
    DEF_VALUE,
    DualListChoice,
    GroupedListOfMultipleChoices,
    JSONValue,
    ListOfMultiple,
    ListOfMultipleChoiceGroup,
    ValueSpec,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
    ValueSpecValidateFunc,
)
from cmk.gui.visuals.filter import Filter, filter_registry
from cmk.gui.visuals.info import visual_info_registry


def FilterChoices(infos: SingleInfos, title: str, help: str) -> DualListChoice:
    """Select names of filters for the given infos"""

    def _info_filter_choices(infos):
        for info in infos:
            info_title = visual_info_registry[info]().title
            for key, filter_ in VisualFilterList.get_choices(info):
                yield (key, f"{info_title}: {filter_.title()}")

    return DualListChoice(
        choices=list(_info_filter_choices(infos)),
        title=title,
        help=help,
    )


class VisualFilter(ValueSpec[FilterHTTPVariables]):
    """Realizes a Multisite/visual filter in a valuespec

    It can render the filter form, get the filled in values and provide the filled in information
    for persistance.
    """

    def __init__(
        self,
        *,
        name: str,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[FilterHTTPVariables] = DEF_VALUE,
        validate: ValueSpecValidateFunc[FilterHTTPVariables] | None = None,
    ):
        self._name = name
        self._filter = filter_registry[name]
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)

    def title(self) -> str:
        return self._filter.title

    def canonical_value(self) -> FilterHTTPVariables:
        return {}

    def render_input(self, varprefix: str, value: FilterHTTPVariables) -> None:
        # A filter can not be used twice on a page, because the varprefix is not used
        show_filter(self._filter, value)

    def from_html_vars(self, varprefix: str) -> FilterHTTPVariables:
        # A filter can not be used twice on a page, because the varprefix is not used
        return self._filter.value()

    def validate_datatype(self, value: FilterHTTPVariables, varprefix: str) -> None:
        if not isinstance(value, dict):
            raise MKUserError(
                varprefix, _("The value must be of type dict, but it has type %s") % type(value)
            )

    def validate_value(self, value: FilterHTTPVariables, varprefix: str) -> None:
        self._filter.validate_value(value)

    def mask(self, value: FilterHTTPVariables) -> FilterHTTPVariables:
        return value

    def value_to_html(self, value: FilterHTTPVariables) -> ValueSpecText:
        raise NotImplementedError()  # FIXME! Violates LSP!

    def value_to_json(self, value: FilterHTTPVariables) -> JSONValue:
        raise NotImplementedError()  # FIXME! Violates LSP!

    def value_from_json(self, json_value: JSONValue) -> FilterHTTPVariables:
        raise NotImplementedError()  # FIXME! Violates LSP!


def show_filter(f: Filter, value: FilterHTTPVariables) -> None:
    html.open_div(class_=["floatfilter", f.ident])
    html.open_div(class_="legend")
    html.span(f.title)
    html.close_div()
    html.open_div(class_="content")
    if f.description:
        html.help(f.description)
    try:
        with output_funnel.plugged():
            f.display(value)
            html.write_html(HTML.without_escaping(output_funnel.drain()))
    except LivestatusTestingError:
        raise
    except Exception as e:
        logger.exception("error showing filter")
        tb = sys.exc_info()[2]
        tbs = ["Traceback (most recent call last):\n"]
        tbs += traceback.format_tb(tb)
        html.icon(
            "alert", _("This filter cannot be displayed") + " ({})\n{}".format(e, "".join(tbs))
        )
        html.write_text_permissive(_("This filter cannot be displayed"))
    html.close_div()
    html.close_div()


class VisualFilterList(ListOfMultiple):
    """Implements a list of available filters for the given infos. By default no
    filter is selected. The user may select a filter to be activated, then the
    filter is rendered and the user can provide a default value.
    """

    @classmethod
    def get_choices(
        cls, info: str, ignored_context_choices: Sequence[str] = ()
    ) -> Sequence[tuple[str, VisualFilter]]:
        return sorted(
            cls._get_filter_specs(info, ignored_context_choices),
            key=lambda x: (x[1]._filter.sort_index, x[1].title()),
        )

    @classmethod
    def _get_filter_specs(
        cls, info: str, ignored_context_choices: Sequence[str]
    ) -> Iterator[tuple[str, VisualFilter]]:
        for fname, filter_ in filters_allowed_for_info(info):
            if fname not in ignored_context_choices:
                yield fname, VisualFilter(name=fname, title=filter_.title)

    def __init__(
        self,
        info_list: SingleInfos,
        ignored_context_choices: Sequence[str] = (),
        title: str | None = None,
        allow_empty: bool = True,
    ) -> None:
        self._filters = filters_allowed_for_infos(info_list)

        if title is None:
            title = _("Filters")

        grouped: GroupedListOfMultipleChoices = [
            ListOfMultipleChoiceGroup(
                title=visual_info_registry[info]().title,
                choices=self.get_choices(info, ignored_context_choices),
            )
            for info in info_list
        ]
        super().__init__(
            choices=grouped,
            choice_page_name="ajax_visual_filter_list_get_choice",
            page_request_vars={
                "infos": info_list,
            },
            allow_empty=allow_empty,
            add_label=_("Add filter"),
            del_label=_("Remove filter"),
            delete_style="filter",
        )

    def from_html_vars(self, varprefix: str) -> VisualContext:
        context = super().from_html_vars(varprefix)
        for values in context.values():
            assert isinstance(values, dict)
            for name, value in values.items():
                assert isinstance(name, str) and isinstance(value, str)
        return context

    def filter_names(self):
        return self._filters.keys()

    def filter_items(self):
        return self._filters.items()

    def has_show_more(self) -> bool:
        return all(vs.is_show_more for _key, vs in self.filter_items())


def filters_allowed_for_info(info: str) -> Iterator[tuple[str, Filter]]:
    """Returns a map of filter names and filter objects that are registered for the given info"""
    for fname, filt in filter_registry.items():
        if filt.info is None or info == filt.info:
            yield fname, filt


def filters_allowed_for_infos(info_list: SingleInfos) -> dict[str, Filter]:
    """Same as filters_allowed_for_info() but for multiple infos"""
    return dict(chain.from_iterable(map(filters_allowed_for_info, info_list)))


def filters_exist_for_infos(infos: SingleInfos) -> bool:
    """Returns True if any filter is registered for the given infos"""
    for _fname, filt in filter_registry.items():
        for info in infos:
            if filt.info is None or info == filt.info:
                return True
    return False


class VisualFilterListWithAddPopup(VisualFilterList):
    """Special form of the visual filter list to be used in the views and dashboards"""

    @staticmethod
    def filter_list_id(varprefix: str) -> str:
        return "%s_popup_filter_list" % varprefix

    def _show_add_elements(self, varprefix: str) -> None:
        filter_list_id = VisualFilterListWithAddPopup.filter_list_id(varprefix)
        filter_list_selected_id = filter_list_id + "_selected"

        show_more = (
            user.get_tree_state("more_buttons", filter_list_id, isopen=False) or user.show_more_mode
        )
        html.open_div(
            id_=filter_list_id, class_=["popup_filter_list", ("more" if show_more else "less")]
        )
        html.more_button(filter_list_id, 1)
        for group in self._grouped_choices:
            if not group.choices:
                continue

            group_id = "filter_group_" + "".join(group.title.split()).lower()

            html.open_div(id_=group_id, class_="filter_group")
            # Show / hide all entries of this group
            with foldable_container(
                treename="filter_group_title",
                id_=group_id,
                isopen=True,
                title=group.title,
                indent=None,
            ):
                # Display all entries of this group
                html.open_ul(class_="active")
                for choice in group.choices:
                    filter_name = choice[0]

                    filter_obj = filter_registry[filter_name]
                    html.open_li(class_="show_more_mode" if filter_obj.is_show_more else "basic")

                    html.a(
                        choice[1].title() or filter_name,
                        href="javascript:void(0)",
                        onclick="cmk.valuespecs.listofmultiple_add(%s, %s, %s, this);"
                        "cmk.page_menu.update_filter_list_scroll(%s)"
                        % (
                            json.dumps(varprefix),
                            json.dumps(self._choice_page_name),
                            json.dumps(self._page_request_vars),
                            json.dumps(filter_list_selected_id),
                        ),
                        id_=f"{varprefix}_add_{filter_name}",
                    )

                    html.close_li()
                html.close_ul()

            html.close_div()
        html.close_div()
        filters_applied = request.get_ascii_input("filled_in") == "filter"
        html.javascript(
            f"cmk.valuespecs.listofmultiple_init({json.dumps(varprefix)}, {json.dumps(filters_applied)});"
        )
        html.javascript("cmk.utils.add_simplebar_scrollbar(%s);" % json.dumps(filter_list_id))


class PageAjaxVisualFilterListGetChoice(ABCPageListOfMultipleGetChoice):
    def _get_choices(self, api_request):
        infos = api_request["infos"]
        return [
            ListOfMultipleChoiceGroup(
                title=visual_info_registry[info]().title, choices=VisualFilterList.get_choices(info)
            )
            for info in infos
        ]
