#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for module internals and the plugins"""

from __future__ import annotations

import abc
import copy
import json
import urllib.parse
from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial
from itertools import chain
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

from livestatus import LivestatusResponse, SiteId

import cmk.utils.plugin_registry
from cmk.utils.macros import MacroMapping, replace_macros_in_str
from cmk.utils.type_defs import UserId

import cmk.gui.sites as sites
import cmk.gui.visuals as visuals
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.config import active_config, default_authorized_builtin_role_ids
from cmk.gui.exceptions import MKGeneralException, MKMissingDataError, MKTimeout, MKUserError
from cmk.gui.figures import create_figures_response, FigureResponseData
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.pages import AjaxPage, page_registry, PageResult
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.plugins.metrics.utils import GraphRenderOptions
from cmk.gui.plugins.views.painters import host_state_short, service_state_short
from cmk.gui.sites import get_alias_of_host
from cmk.gui.type_defs import (
    ColumnName,
    FilterName,
    HTTPVariables,
    Icon,
    LinkFromSpec,
    PainterSpec,
    RoleName,
    Row,
    SingleInfos,
    SorterSpec,
    TypedVisual,
    VisualContext,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.rendering import text_with_links_to_user_translated_html
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.urls import makeuri, makeuri_contextless, urlencode_vars
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DictionaryElements,
    DictionaryEntry,
    DropdownChoice,
    FixedValue,
    MigrateNotUpdated,
    TextInput,
    TimerangeValue,
    ValueSpec,
    ValueSpecValidateFunc,
)
from cmk.gui.view_store import get_all_views, get_permitted_views, internal_view_to_runtime_view

DashboardName = str


class DashboardConfig(TypedVisual):
    mtime: int
    dashlets: list[DashletConfig]
    show_title: bool
    mandatory_context_filters: list[FilterName]


class _DashletConfigMandatory(TypedDict):
    type: str


class DashletConfig(_DashletConfigMandatory, total=False):
    single_infos: SingleInfos
    title: str
    title_url: str
    context: VisualContext
    # TODO: Could not a place which sets this flag. Can we remove it?
    reload_on_resize: bool
    position: DashletPosition
    size: DashletSize
    background: bool
    show_title: bool | Literal["transparent"]


class ABCViewDashletConfig(DashletConfig):
    name: str


class LinkedViewDashletConfig(ABCViewDashletConfig):
    ...


class _ViewDashletConfigMandatory(ABCViewDashletConfig):
    # TODO: Find a way to clean up the rendundancies with ViewSpec and Visual
    # From: Visual
    owner: str
    # These fields are redundant between DashletConfig and Visual
    # name: str
    # context: VisualContext
    # single_infos: SingleInfos
    # title: str | LazyString
    add_context_to_title: bool
    description: str | LazyString
    topic: str
    sort_index: int
    is_show_more: bool
    icon: Icon | None
    hidden: bool
    hidebutton: bool
    public: bool | tuple[Literal["contact_groups"], Sequence[str]]
    # From: ViewSpec
    datasource: str
    layout: str  # TODO: Replace with literal? See layout_registry.get_choices()
    group_painters: list[PainterSpec]
    painters: list[PainterSpec]
    browser_reload: int
    num_columns: int
    column_headers: Literal["off", "pergroup", "repeat"]
    sorters: Sequence[SorterSpec]


class ViewDashletConfig(_ViewDashletConfigMandatory, total=False):
    # TODO: Find a way to clean up the rendundancies with ViewSpec and Visual
    # From: Visual
    link_from: LinkFromSpec
    # From: ViewSpec
    add_headers: str
    # View editor only adds them in case they are truish. In our builtin specs these flags are also
    # partially set in case they are falsy
    mobile: bool
    mustsearch: bool
    force_checkboxes: bool
    user_sortable: bool
    play_sounds: bool


class ABCGraphDashletConfig(DashletConfig):
    timerange: TimerangeValue
    graph_render_options: GraphRenderOptions


DashletTypeName = str
DashletId = int
DashletRefreshInterval = Union[bool, int]
DashletRefreshAction = Optional[str]
DashletSize = Tuple[int, int]
DashletPosition = Tuple[int, int]
DashletInputFunc = Callable[[DashletConfig], None]
DashletHandleInputFunc = Callable[[DashletId, DashletConfig, DashletConfig], DashletConfig]

builtin_dashboards: Dict[DashboardName, DashboardConfig] = {}

# Declare constants to be used in the definitions of the dashboards
GROW = 0
MAX = -1


def macro_mapping_from_context(
    context: VisualContext,
    single_infos: SingleInfos,
    title: str,
    default_title: str,
    **additional_macros: str,
) -> MacroMapping:
    macro_mapping = {"$DEFAULT_TITLE$": default_title}
    macro_mapping.update(
        {
            macro: context[key][key]
            for macro, key in (
                ("$HOST_NAME$", "host"),
                ("$SERVICE_DESCRIPTION$", "service"),
            )
            if key in context and key in context[key] and key in single_infos
        }
    )

    if "$HOST_ALIAS$" in title and "$HOST_NAME$" in macro_mapping:
        macro_mapping["$HOST_ALIAS$"] = get_alias_of_host(
            SiteId(additional_macros.get("$SITE$", "")),
            macro_mapping["$HOST_NAME$"],
        )

    macro_mapping.update(additional_macros)

    return macro_mapping


def render_title_with_macros_string(  # type:ignore[no-untyped-def]
    context: VisualContext,
    single_infos: SingleInfos,
    title: str,
    default_title: str,
    **additional_macros: str,
):
    return replace_macros_in_str(
        _u(title),
        macro_mapping_from_context(
            context,
            single_infos,
            title,
            default_title,
            **additional_macros,
        ),
    )


T = TypeVar("T", bound=DashletConfig)


class Dashlet(abc.ABC, Generic[T]):
    """Base class for all dashboard dashlet implementations"""

    # Minimum width and height of dashlets in raster units
    minimum_size: DashletSize = (12, 12)

    @classmethod
    @abc.abstractmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def description(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def sort_index(cls) -> int:
        raise NotImplementedError()

    @classmethod
    def has_context(cls) -> bool:
        """Whether or not this dashlet is context sensitive."""
        return False

    @classmethod
    def single_infos(cls) -> SingleInfos:
        """Return a list of the single infos (for the visual context) of this dashlet"""
        return []

    @classmethod
    def is_selectable(cls) -> bool:
        """Whether or not the user can choose to add this dashlet in the dashboard editor"""
        return True

    @classmethod
    def is_resizable(cls) -> bool:
        """Whether or not the user may resize this dashlet"""
        return True

    @classmethod
    def is_iframe_dashlet(cls) -> bool:
        """Whether or not the dashlet is rendered in an iframe"""
        return False

    @classmethod
    def initial_size(cls) -> DashletSize:
        """The initial size of dashlets when being added to the dashboard"""
        return cls.minimum_size

    @classmethod
    def initial_position(cls) -> DashletPosition:
        """The initial position of dashlets when being added to the dashboard"""
        return (1, 1)

    @classmethod
    def initial_refresh_interval(cls) -> DashletRefreshInterval:
        return False

    @classmethod
    def vs_parameters(
        cls,
    ) -> None | list[DictionaryEntry] | ValueSpec | tuple[
        Callable[[T], None], Callable[[DashletId, T, T], T]
    ]:
        """Returns a valuespec instance in case the dashlet has parameters, otherwise None"""
        # For legacy reasons this may also return a list of Dashboard() elements. (TODO: Clean this up)
        return None

    @classmethod
    def opt_parameters(cls) -> Union[bool, List[str]]:
        """List of optional parameters in case vs_parameters() returns a list"""
        return False

    @classmethod
    def validate_parameters_func(cls) -> Optional[ValueSpecValidateFunc[Any]]:
        """Optional validation function in case vs_parameters() returns a list"""
        return None

    @classmethod
    def styles(cls) -> Optional[str]:
        """Optional registration of snapin type specific stylesheets"""
        return None

    @classmethod
    def script(cls) -> Optional[str]:
        """Optional registration of snapin type specific javascript"""
        return None

    @classmethod
    def allowed_roles(cls) -> list[RoleName]:
        return default_authorized_builtin_role_ids

    @classmethod
    def add_url(cls) -> str:
        """The URL to open for adding a new dashlet of this type to a dashboard"""
        return makeuri(
            request,
            [("type", cls.type_name()), ("back", makeuri(request, [("edit", "1")]))],
            filename="edit_dashlet.py",
        )

    @classmethod
    def default_settings(cls):
        """Overwrite specific default settings for dashlets by returning a dict
            return { key: default_value, ... }
        e.g. to have a dashlet default to not showing its title
            return { "show_title": False }
        """
        return {}

    def __init__(
        self,
        dashboard_name: DashboardName,
        dashboard: DashboardConfig,
        dashlet_id: DashletId,
        dashlet: T,
    ) -> None:
        super().__init__()
        self._dashboard_name = dashboard_name
        self._dashboard = dashboard
        self._dashlet_id = dashlet_id
        self._dashlet_spec = dashlet
        self._context: Optional[VisualContext] = self._get_context()

    def infos(self) -> SingleInfos:
        """Return a list of the supported infos (for the visual context) of this dashlet"""
        return []

    def _get_context(self) -> Optional[VisualContext]:
        if not self.has_context():
            return None

        return visuals.get_merged_context(
            self._dashboard["context"],
            self._dashlet_spec["context"],
        )

    @property
    def context(self) -> VisualContext:
        if self._context is None:
            raise Exception("Missing context")
        return self._context

    @property
    def dashlet_id(self) -> DashletId:
        return self._dashlet_id

    @property
    def dashlet_spec(self) -> T:
        return self._dashlet_spec

    @property
    def dashboard_name(self) -> str:
        return self._dashboard_name

    def default_display_title(self) -> str:
        return self.title()

    def display_title(self) -> str:
        try:
            return self._dashlet_spec["title"]
        except KeyError:
            return self.default_display_title()

    def _get_macro_mapping(self, title: str) -> MacroMapping:
        return macro_mapping_from_context(
            self.context if self.has_context() else {},
            self.single_infos(),
            title,
            self.default_display_title(),
        )

    def render_title_html(self) -> HTML:
        title = self.display_title()
        return text_with_links_to_user_translated_html(
            [
                (
                    replace_macros_in_str(
                        title,
                        self._get_macro_mapping(title),
                    ),
                    self.title_url(),
                ),
            ],
        )

    def show_title(self) -> bool | Literal["transparent"]:
        try:
            return self._dashlet_spec["show_title"]
        except KeyError:
            return True

    def title_url(self) -> Optional[str]:
        try:
            return self._dashlet_spec["title_url"]
        except KeyError:
            return None

    def show_background(self) -> bool:
        try:
            return self._dashlet_spec["background"]
        except KeyError:
            return True

    def on_resize(self) -> Optional[str]:
        """Returns either Javascript code to execute when a resize event occurs or None"""
        return None

    def on_refresh(self) -> Optional[str]:
        """Returns either Javascript code to execute when a the dashlet should be refreshed or None"""
        return None

    def update(self) -> None:
        """Called by the ajax call to update dashlet contents

        This is normally equivalent to the .show() method. Differs only for
        iframe and single metric dashlets.
        """
        self.show()

    @abc.abstractmethod
    def show(self) -> None:
        """Produces the HTML code of the dashlet content."""
        raise NotImplementedError()

    def _add_context_vars_to_url(self, url: str) -> str:
        """Adds missing context variables to the given URL"""
        if not self.has_context():
            return url

        context_vars = {k: str(v) for k, v in self._dashlet_context_vars() if v is not None}  #

        # This is a long distance hack to be able to rebuild the variables on the dashlet _get_context
        # using the visuals.VisualFilterListWithAddPopup.from_html_vars, which
        # requires this flag.
        parts = urllib.parse.urlparse(url)
        url_vars = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
        url_vars.update(context_vars)

        new_qs = urllib.parse.urlencode(url_vars)
        return urllib.parse.urlunparse(tuple(parts[:4] + (new_qs,) + parts[5:]))

    def _dashlet_context_vars(self) -> list[tuple[str, str]]:
        return visuals.context_to_uri_vars(self.context)

    def unconfigured_single_infos(self) -> Set[str]:
        """Returns infos that are not set by the dashlet config"""
        if not self.has_context():
            return set()
        return visuals.get_missing_single_infos(self.single_infos(), self._dashlet_spec["context"])

    def missing_single_infos(self) -> Set[str]:
        """Returns infos that are neither configured nor available through HTTP variables"""
        if not self.has_context():
            return set()
        return visuals.get_missing_single_infos(self.single_infos(), self.context)

    def size(self) -> DashletSize:
        if self.is_resizable():
            try:
                return self._dashlet_spec["size"]
            except KeyError:
                return self.initial_size()
        return self.initial_size()

    def position(self) -> DashletPosition:
        try:
            return self._dashlet_spec["position"]
        except KeyError:
            return self.initial_position()

    def refresh_interval(self) -> DashletRefreshInterval:
        return self.initial_refresh_interval()

    def get_refresh_action(self) -> DashletRefreshAction:
        if not self.refresh_interval():
            return None

        url = self._get_refresh_url()
        try:
            # pylint is just too stupid, see e.g. https://github.com/PyCQA/pylint/issues/2332
            # or https://github.com/PyCQA/pylint/issues/2559 plus a dozen other issues...
            on_refresh = self.on_refresh()  # pylint: disable=assignment-from-none
            if on_refresh:
                return "(function() {%s})" % on_refresh
            return '"%s"' % self._add_context_vars_to_url(url)  # url to dashboard_dashlet.py
        except Exception:
            # Ignore the exceptions in non debug mode, assuming the exception also occures
            # while dashlet rendering, which is then shown in the dashlet itselfs.
            if active_config.debug:
                raise

        return None

    def _get_refresh_url(self) -> str:
        """Returns the URL to be used for loading the dashlet contents"""
        return makeuri_contextless(
            request,
            [
                ("name", self._dashboard_name),
                ("id", self._dashlet_id),
                ("mtime", self._dashboard["mtime"]),
            ],
            filename="dashboard_dashlet.py",
        )

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield from []


def _get_title_macros_from_single_infos(single_infos: SingleInfos) -> Iterable[str]:
    single_info_to_macros = {
        "host": ("$HOST_NAME$", "$HOST_ALIAS$"),
        "service": ("$SERVICE_DESCRIPTION$",),
    }
    for single_info in sorted(single_infos):
        yield from single_info_to_macros.get(single_info, [])


def _title_help_text_for_macros(dashlet_type: Type[Dashlet]) -> str:
    available_macros = chain(
        ["$DEFAULT_TITLE$ " + _u("(default title of the element)")],
        _get_title_macros_from_single_infos(dashlet_type.single_infos()),
        dashlet_type.get_additional_title_macros(),
    )
    macros_as_list = (
        f"<ul>{''.join(f'<li><tt>{macro}</tt></li>' for macro in available_macros)}</ul>"
    )
    return _("You can use the following macros to fill in the corresponding information:%s%s") % (
        macros_as_list,
        _(
            'These macros can be combined with arbitrary text elements, e.g. "some text '
            '<tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>".'
        ),
    )


def dashlet_vs_general_settings(
    dashlet_type: Type[Dashlet], single_infos: SingleInfos
) -> Dictionary:
    return Dictionary(
        title=_("General Settings"),
        render="form",
        optional_keys=["title", "title_url"],
        elements=[
            (
                "type",
                FixedValue(
                    value=dashlet_type.type_name(),
                    totext=dashlet_type.title(),
                    title=_("Element type"),
                ),
            ),
            visuals.single_infos_spec(single_infos),
            (
                "background",
                Checkbox(
                    title=_("Colored background"),
                    label=_("Render background"),
                    help=_("Render gray background color behind the elements content."),
                    default_value=True,
                ),
            ),
            (
                "show_title",
                DropdownChoice(
                    title=_("Show title header"),
                    help=_("Render the titlebar including title and link above the element."),
                    choices=[
                        (False, _("Don't show any header")),
                        (True, _("Show header with highlighted background")),
                        ("transparent", _("Show title without any background")),
                    ],
                    default_value=True,
                ),
            ),
            (
                "title",
                TextInput(
                    title=_("Custom title") + "<sup>*</sup>",
                    placeholder=_(
                        "This option is macro-capable, please check the inline help for more "
                        "information."
                    ),
                    help=" ".join(
                        (
                            _(
                                "Most elements have a hard coded static title and some are aware of their "
                                "content and set the title dynamically, like the view snapin, which "
                                "displays the title of the view. If you like to use any other title, set it "
                                "here."
                            ),
                            _title_help_text_for_macros(dashlet_type),
                        )
                    ),
                    size=75,
                ),
            ),
            (
                "title_url",
                TextInput(
                    title=_("Link of Title"),
                    help=_("The URL of the target page the link of the element should link to."),
                    size=50,
                ),
            ),
        ],
    )


class IFrameDashlet(Dashlet[T], abc.ABC):
    """Base class for all dashlet using an iframe"""

    @classmethod
    def is_iframe_dashlet(cls) -> bool:
        """Whether or not the dashlet is rendered in an iframe"""
        return True

    def show(self) -> None:
        self._show_initial_iframe_container()

    def reload_on_resize(self) -> bool:
        """Whether or not the page should be reloaded when the dashlet is resized"""
        try:
            return self._dashlet_spec["reload_on_resize"]
        except KeyError:
            return False

    def _show_initial_iframe_container(self) -> None:
        iframe_url = self._get_iframe_url()
        if not iframe_url:
            return

        # Fix of iPad >:-P
        html.open_div(style="width: 100%; height: 100%; -webkit-overflow-scrolling:touch;")
        html.iframe(
            "",
            src="about:blank" if self.reload_on_resize() else iframe_url,
            id_="dashlet_iframe_%d" % self._dashlet_id,
            allowTransparency="true",
            frameborder="0",
            width="100%",
            height="100%",
        )
        html.close_div()

        if self.reload_on_resize():
            html.javascript(
                "cmk.dashboard.set_reload_on_resize(%s, %s);"
                % (json.dumps(self._dashlet_id), json.dumps(iframe_url))
            )

    def _get_iframe_url(self) -> Optional[str]:
        if not self.is_iframe_dashlet():
            return None

        return self._add_context_vars_to_url(self._get_refresh_url())

    @abc.abstractmethod
    def update(self) -> None:
        raise NotImplementedError()


class DashletRegistry(cmk.utils.plugin_registry.Registry[Type[Dashlet]]):
    """The management object for all available plugins."""

    def plugin_name(self, instance):
        return instance.type_name()


dashlet_registry = DashletRegistry()


@page_registry.register_page("ajax_figure_dashlet_data")
class FigureDashletPage(AjaxPage):
    def page(self) -> PageResult:
        dashboard_name = request.get_ascii_input_mandatory("name")
        try:
            dashboard = get_permitted_dashboards()[dashboard_name]
        except KeyError:
            raise MKUserError("name", _("The requested dashboard does not exist."))
        # Get context from the AJAX request body (not simply from the dashboard config) to include
        # potential dashboard context given via HTTP request variables
        dashboard["context"] = json.loads(request.get_ascii_input_mandatory("context"))

        dashlet_id = request.get_integer_input_mandatory("id")
        try:
            dashlet_spec = dashboard["dashlets"][dashlet_id]
        except IndexError:
            raise MKUserError("id", _("The element does not exist."))

        try:
            dashlet_type = cast(Type[ABCFigureDashlet], dashlet_registry[dashlet_spec["type"]])
        except KeyError:
            raise MKUserError("type", _("The requested element type does not exist."))

        dashlet = dashlet_type(dashboard_name, dashboard, dashlet_id, dashlet_spec)
        return create_figures_response(dashlet.generate_response_data())


class ABCFigureDashlet(Dashlet[T], abc.ABC):
    """Base class for cmk_figures based graphs
    Only contains the dashlet spec, the data generation is handled in the
    DataGenerator classes, to split visualization and data
    """

    @classmethod
    def type_name(cls) -> str:
        return "figure_dashlet"

    @classmethod
    def sort_index(cls) -> int:
        return 95

    @classmethod
    def initial_refresh_interval(cls) -> bool:
        return False

    @classmethod
    def initial_size(cls) -> DashletSize:
        return (56, 40)

    def infos(self) -> SingleInfos:
        return ["host", "service"]

    @classmethod
    def single_infos(cls) -> SingleInfos:
        return []

    @classmethod
    def has_context(cls) -> bool:
        return True

    @property
    def instance_name(self) -> str:
        # Note: This introduces the restriction one graph type per dashlet
        return "%s_%s" % (self.type_name(), self._dashlet_id)

    @classmethod
    def vs_parameters(cls) -> MigrateNotUpdated:
        return MigrateNotUpdated(
            valuespec=Dictionary(
                title=_("Properties"),
                render="form",
                optional_keys=cls._vs_optional_keys(),
                elements=cls._vs_elements(),
            ),
            migrate=cls._migrate_vs,
        )

    @staticmethod
    def _vs_optional_keys() -> Union[bool, list[str]]:
        return False

    @staticmethod
    def _migrate_vs(valuespec_result):
        if "svc_status_display" in valuespec_result:
            # now as code is shared between host and service (svc) dashlet,
            # the `svc_` prefix is removed.
            valuespec_result["status_display"] = valuespec_result.pop("svc_status_display")
        return valuespec_result

    @staticmethod
    def _vs_elements() -> DictionaryElements:
        return []

    @abc.abstractmethod
    def generate_response_data(self) -> FigureResponseData:
        ...

    @property
    def update_interval(self) -> int:
        return 60

    def on_resize(self):
        return ("if (typeof %(instance)s != 'undefined') {" "%(instance)s.update_gui();" "}") % {
            "instance": self.instance_name
        }

    def show(self) -> None:
        self.js_dashlet(figure_type_name=self.type_name())

    def js_dashlet(self, figure_type_name: str) -> None:
        fetch_url = "ajax_figure_dashlet_data.py"
        div_id = "%s_dashlet_%d" % (self.type_name(), self._dashlet_id)
        html.div("", id_=div_id)

        # TODO: Would be good to align this scheme with AjaxPage.webapi_request()
        # (a single HTTP variable "request=<json-body>".
        post_body = urlencode_vars(self._dashlet_http_variables())

        html.javascript(
            """
            let figure_%(dashlet_id)d = cmk.figures.figure_registry.get_figure(%(type_name)s);
            let %(instance_name)s = new figure_%(dashlet_id)d(%(div_selector)s);
            %(instance_name)s.set_post_url_and_body(%(url)s, %(body)s);
            %(instance_name)s.set_dashlet_spec(%(dashlet_spec)s);
            %(instance_name)s.initialize();
            %(instance_name)s.scheduler.set_update_interval(%(update)d);
            %(instance_name)s.scheduler.enable();
            """
            % {
                "type_name": json.dumps(figure_type_name),
                "dashlet_id": self._dashlet_id,
                "dashlet_spec": json.dumps(self.dashlet_spec),
                "instance_name": self.instance_name,
                "div_selector": json.dumps("#%s" % div_id),
                "url": json.dumps(fetch_url),
                "body": json.dumps(post_body),
                "update": self.update_interval,
            }
        )

    def _dashlet_http_variables(self) -> HTTPVariables:
        return [
            ("name", self.dashboard_name),
            ("id", self.dashlet_id),
            # Add context to the dashlet's AJAX request body so any dashboard context that is given
            # via HTTP request is not lost in the AJAX call
            ("context", json.dumps(self._dashboard["context"])),
        ]


def _internal_dashboard_to_runtime_dashboard(raw_dashboard: dict[str, Any]) -> DashboardConfig:
    return {
        # Need to assume that we are right for now. We will have to introduce parsing there to do a
        # real conversion in one of the following typing steps
        **raw_dashboard,  # type: ignore[misc]
        "dashlets": [
            internal_view_to_runtime_view(dashlet_spec)
            if dashlet_spec["type"] == "view"
            else dashlet_spec
            for dashlet_spec in raw_dashboard["dashlets"]
        ],
    }


# TODO: Same as in cmk.gui.plugins.views.utils.ViewStore, centralize implementation?
class DashboardStore:
    @classmethod
    @request_memoize()
    def get_instance(cls):
        """Load dashboards only once for each request"""
        return cls()

    def __init__(self) -> None:
        self.all = self._load_all()
        self.permitted = self._load_permitted(self.all)

    def _load_all(self) -> Dict[Tuple[UserId, DashboardName], DashboardConfig]:
        """Loads all definitions from disk and returns them"""
        return visuals.load(
            "dashboards",
            builtin_dashboards,
            _internal_dashboard_to_runtime_dashboard,
        )

    def _load_permitted(
        self, all_dashboards: Dict[Tuple[UserId, DashboardName], DashboardConfig]
    ) -> Dict[DashboardName, DashboardConfig]:
        """Returns all defitions that a user is allowed to use"""
        return visuals.available("dashboards", all_dashboards)


def save_all_dashboards() -> None:
    visuals.save("dashboards", get_all_dashboards())


def get_all_dashboards() -> dict[tuple[UserId, DashboardName], DashboardConfig]:
    return DashboardStore.get_instance().all


def get_permitted_dashboards() -> dict[DashboardName, DashboardConfig]:
    return DashboardStore.get_instance().permitted


def copy_view_into_dashlet(
    dashlet: ViewDashletConfig,
    nr: DashletId,
    view_name: str,
    add_context: Optional[VisualContext] = None,
    load_from_all_views: bool = False,
) -> None:
    permitted_views = get_permitted_views()

    # it is random which user is first accessing
    # an apache python process, initializing the dashboard loading and conversion of
    # old dashboards. In case of the conversion we really try hard to make the conversion
    # work in all cases. So we need all views instead of the views of the user.
    if load_from_all_views and view_name not in permitted_views:
        # This is not really 100% correct according to the logic of visuals.available(),
        # but we do this for the rare edge case during legacy dashboard conversion, so
        # this should be sufficient
        for (_unused, n), this_view in get_all_views().items():
            # take the first view with a matching name
            if view_name == n:
                view = this_view
                break

        if not view:
            raise MKGeneralException(
                _(
                    "Failed to convert a builtin dashboard which is referencing "
                    'the view "%s". You will have to migrate it to the new '
                    "dashboard format on your own to work properly."
                )
                % view_name
            )
    else:
        view = permitted_views[view_name]

    view = copy.deepcopy(view)  # Clone the view

    # the view definition may contain lazy strings that will be serialized to 'l"to translate"' when
    # saving the view data structure. Which will later cause an SyntaxError when trying to load the
    # .mk file. Resolve these strings here to prevent that issue.
    view["title"] = str(view["title"])
    view["description"] = str(view["description"])

    # TODO: Can hopefully be claned up once view is also a TypedDict
    dashlet.update(view)  # type: ignore[typeddict-item]
    if add_context:
        dashlet["context"] = {**dashlet["context"], **add_context}

    # Overwrite the views default title with the context specific title
    dashlet["title"] = visuals.visual_title("view", view, dashlet["context"])
    # TODO: Shouldn't we use the self._dashlet_context_vars() here?
    name_part: HTTPVariables = [("view_name", view_name)]
    singlecontext_vars = cast(
        HTTPVariables,
        list(
            visuals.get_singlecontext_vars(
                view["context"],
                view["single_infos"],
            ).items()
        ),
    )
    dashlet["title_url"] = makeuri_contextless(
        request,
        name_part + singlecontext_vars,
        filename="view.py",
    )

    dashlet["type"] = "view"
    dashlet["name"] = "dashlet_%d" % nr
    dashlet["show_title"] = True
    dashlet["mustsearch"] = False


def host_table_query(
    context: VisualContext, columns: Iterable[ColumnName]
) -> tuple[list[ColumnName], LivestatusResponse]:
    return _table_query(context, "hosts", columns, ["host"])


def service_table_query(
    context: VisualContext, columns: Iterable[ColumnName]
) -> tuple[list[ColumnName], LivestatusResponse]:
    return _table_query(context, "services", columns, ["host", "service"])


def _table_query(
    context: VisualContext, table: str, columns: Iterable[ColumnName], infos: List[str]
) -> tuple[list[ColumnName], LivestatusResponse]:
    filter_headers, only_sites = visuals.get_filter_headers(table, infos, context)

    query = (
        f"GET {table}\n"
        "Columns: %(cols)s\n"
        "%(filter)s"
        % {
            "cols": " ".join(columns),
            "filter": filter_headers,
        }
    )

    with sites.only_sites(only_sites), sites.prepend_site():
        try:
            rows = sites.live().query(query)
        except MKTimeout:
            raise
        except Exception:
            raise MKGeneralException(_("The query returned no data."))

    return ["site"] + list(columns), rows


def create_host_view_url(context):
    return makeuri_contextless(
        request,
        [
            ("view_name", "host"),
            ("site", context["site"]),
            ("host", context["host_name"]),
        ],
        filename="view.py",
    )


def create_service_view_url(context):
    return makeuri_contextless(
        request,
        [
            ("view_name", "service"),
            ("site", context["site"]),
            ("host", context["host_name"]),
            ("service", context["service_description"]),
        ],
        filename="view.py",
    )


def dashboard_breadcrumb(
    name: str, board: DashboardConfig, title: str, context: VisualContext
) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(
        mega_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic(board["topic"]).title(),
    )

    if "kubernetes" in name:
        return kubernetes_dashboard_breadcrumb(name, board, title, breadcrumb, context)

    breadcrumb.append(BreadcrumbItem(title, makeuri(request, [("name", name)])))
    return breadcrumb


def kubernetes_dashboard_breadcrumb(
    name: str, board: DashboardConfig, title: str, breadcrumb: Breadcrumb, context: VisualContext
) -> Breadcrumb:
    """Realize the Kubernetes hierarchy breadcrumb

    Kubernetes (overview board)
     |
     + Kubernetes Cluster
       |
       + Kubernetes Namespace
         |
         + Kubernetes [DaemonSet|StatefulSet|Deployment]
    """
    k8s_ids: Dict[str, str] = {
        ident: "kubernetes_%s" % ident
        for ident in [
            "overview",
            "cluster",
            "cluster-host",  # for the host label only; not a dashboard name
            "namespace",
            "daemonset",
            "statefulset",
            "deployment",
        ]
    }
    # Overview
    breadcrumb.append(
        BreadcrumbItem("Kubernetes", makeuri_contextless(request, [("name", k8s_ids["overview"])]))
    )
    if name == k8s_ids["overview"]:
        return breadcrumb

    # Cluster
    cluster_name: str | None = context.get(k8s_ids["cluster"], {}).get(k8s_ids["cluster"])
    cluster_host: str | None = (
        # take current host from context, if on the cluster dashboard
        context.get("host", {}).get("host")
        if name == k8s_ids["cluster"]
        # else take the cluster-host from request (url)
        else request.get_str_input(k8s_ids["cluster-host"])
    )
    if not (cluster_name and cluster_host):
        breadcrumb.append(BreadcrumbItem(title, makeuri(request, [("name", name)])))
        return breadcrumb
    add_vars: HTTPVariables = [
        ("site", context.get("site", {}).get("site")),
        (k8s_ids["cluster"], cluster_name),
        (k8s_ids["cluster-host"], cluster_host),
    ]
    breadcrumb.append(
        BreadcrumbItem(
            f"Cluster {cluster_name}",
            makeuri_contextless(
                request,
                [
                    ("name", k8s_ids["cluster"]),
                    ("host", cluster_host),
                    *add_vars,
                ],
            ),
        )
    )
    if name == k8s_ids["cluster"]:
        return breadcrumb

    # Namespace
    namespace_name: str | None = context.get(k8s_ids["namespace"], {}).get(k8s_ids["namespace"])
    if not namespace_name:
        breadcrumb.append(BreadcrumbItem(title, makeuri(request, [("name", name)])))
        return breadcrumb
    add_vars.append((k8s_ids["namespace"], namespace_name))
    breadcrumb.append(
        BreadcrumbItem(
            f"Namespace {namespace_name}",
            makeuri_contextless(
                request,
                [
                    ("name", k8s_ids["namespace"]),
                    ("host", f"namespace_{cluster_name}_{namespace_name}"),
                    *add_vars,
                ],
            ),
        )
    )
    if name == k8s_ids["namespace"]:
        return breadcrumb

    # [DaemonSet|StatefulSet|Deployment]
    for obj_type, obj_type_camelcase in [
        ("daemonset", "DaemonSet"),
        ("statefulset", "StatefulSet"),
        ("deployment", "Deployment"),
    ]:
        if obj_name := context.get(k8s_ids[obj_type], {}).get(k8s_ids[obj_type]):
            title = f"{obj_type_camelcase} {obj_name}"
            add_vars.append((k8s_ids[obj_type], obj_name))
            host_name = "_".join([obj_type, cluster_name, namespace_name, obj_name])
            breadcrumb.append(
                BreadcrumbItem(
                    title,
                    makeuri_contextless(
                        request, [("name", k8s_ids[obj_type]), ("host", host_name), *add_vars]
                    ),
                )
            )
            break
    if not obj_name:
        breadcrumb.append(BreadcrumbItem(title, makeuri(request, [("name", name)])))

    return breadcrumb


def purge_metric_for_js(metric):
    return {
        "bounds": metric.get("scalar", {}),
        "unit": {k: v for k, v in metric["unit"].items() if k in ["js_render", "stepping"]},
    }


def make_mk_missing_data_error() -> MKMissingDataError:
    return MKMissingDataError(_("No data was found with the current parameters of this dashlet."))


@dataclass
class StateFormatter:
    css: str
    _state_names: Callable[[Row], Tuple[str, str]]
    message_template: str

    def state_names(self, row: Row) -> Tuple[str, str]:
        return self._state_names(row)


class ServiceStateFormatter(StateFormatter):
    def __init__(self, message_template: str = "{}") -> None:
        super().__init__(
            css="svcstate state{}",
            _state_names=service_state_short,
            message_template=message_template,
        )
        self.css = "svcstate state{}"
        self._state_names = service_state_short
        self.message_template = message_template


def state_map(  # type:ignore[no-untyped-def]
    conf: Optional[Tuple[str, str]], row: Row, formatter: StateFormatter
):
    style = dict(zip(("paint", "status"), conf)) if isinstance(conf, tuple) else {}
    state, status_name = formatter.state_names(row)
    return {
        "css": formatter.css.format(state),
        "msg": formatter.message_template.format(status_name),
        **style,
    }


host_map = partial(
    state_map,
    formatter=StateFormatter(
        "hoststate hstate{}",
        host_state_short,
        "{}",
    ),
)
svc_map = partial(
    state_map,
    formatter=ServiceStateFormatter(),
)
