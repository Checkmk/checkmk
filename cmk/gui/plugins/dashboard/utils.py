#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for module internals and the plugins"""

import abc
import copy
import json
import time
import urllib.parse
from dataclasses import dataclass
from functools import partial
from itertools import chain
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypedDict,
    Union,
)

from livestatus import LivestatusColumn, LivestatusResponse, SiteId

import cmk.utils.plugin_registry
from cmk.utils.macros import MacroMapping, replace_macros_in_str
from cmk.utils.site import omd_site
from cmk.utils.type_defs import UserId

import cmk.gui.sites as sites
import cmk.gui.utils.escaping as escaping
import cmk.gui.visuals as visuals
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.config import builtin_role_ids
from cmk.gui.exceptions import MKGeneralException, MKMissingDataError, MKTimeout, MKUserError
from cmk.gui.figures import create_figures_response
from cmk.gui.globals import config, html, request
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _, _u
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.metrics import translate_perf_data
from cmk.gui.pages import AjaxPage, page_registry
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.plugins.metrics.rrd_fetch import merge_multicol
from cmk.gui.plugins.metrics.valuespecs import transform_graph_render_options
from cmk.gui.plugins.views.painters import host_state_short, service_state_short
from cmk.gui.plugins.views.utils import get_all_views, get_permitted_views, transform_painter_spec
from cmk.gui.sites import get_alias_of_host
from cmk.gui.type_defs import HTTPVariables, Row, SingleInfos, TranslatedMetric, VisualContext
from cmk.gui.utils.html import HTML
from cmk.gui.utils.rendering import text_with_links_to_user_translated_html
from cmk.gui.utils.urls import makeuri, makeuri_contextless, urlencode_vars
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DictionaryElements,
    DictionaryEntry,
    DropdownChoice,
    FixedValue,
    TextInput,
    Transform,
    ValueSpec,
    ValueSpecValidateFunc,
)

DashboardName = str
DashboardConfig = Dict[str, Any]
DashletConfig = Dict[str, Any]

DashletTypeName = str
DashletType = Dict[DashletTypeName, Any]
DashletId = int
DashletRefreshInterval = Union[bool, int]
DashletRefreshAction = Optional[str]
DashletSize = Tuple[int, int]
DashletPosition = Tuple[int, int]
DashletInputFunc = Callable[[DashletType], None]
DashletHandleInputFunc = Callable[[DashletId, DashletConfig], DashletType]

builtin_dashboards: Dict[DashboardName, DashboardConfig] = {}
# Keep this for legacy reasons until we drop the legacy plugin mechanic
dashlet_types: Dict[str, DashletType] = {}

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


def render_title_with_macros_string(
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


class Dashlet(abc.ABC):
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
    def single_infos(cls) -> List[str]:
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
    ) -> Union[
        None, List[DictionaryEntry], ValueSpec, Tuple[DashletInputFunc, DashletHandleInputFunc]
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
    def allowed_roles(cls) -> List[str]:
        return builtin_role_ids

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
        dashlet: DashletConfig,
    ) -> None:
        super().__init__()
        self._dashboard_name = dashboard_name
        self._dashboard = dashboard
        self._dashlet_id = dashlet_id
        self._dashlet_spec = dashlet
        self._context: Optional[VisualContext] = self._get_context()

    def infos(self) -> List[str]:
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
    def dashlet_spec(self) -> DashletConfig:
        return self._dashlet_spec

    @property
    def dashboard_name(self) -> str:
        return self._dashboard_name

    def default_display_title(self) -> str:
        return self.title()

    def display_title(self) -> str:
        return self._dashlet_spec.get("title", self.default_display_title())

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

    def show_title(self) -> bool:
        return self._dashlet_spec.get("show_title", True)

    def title_url(self) -> Optional[str]:
        return self._dashlet_spec.get("title_url")

    def show_background(self) -> bool:
        return self._dashlet_spec.get("background", True)

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

    def _dashlet_context_vars(self) -> HTTPVariables:
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
            return self._dashlet_spec.get("size", self.initial_size())
        return self.initial_size()

    def position(self) -> DashletPosition:
        return self._dashlet_spec.get("position", self.initial_position())

    def refresh_interval(self) -> DashletRefreshInterval:
        return self._dashlet_spec.get("refresh", self.initial_refresh_interval())

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
            if config.debug:
                raise

        return None

    def _get_refresh_url(self) -> str:
        """Returns the URL to be used for loading the dashlet contents"""
        dashlet_url = self._get_dashlet_url_from_urlfunc()
        if dashlet_url is not None:
            return dashlet_url

        if self._dashlet_spec.get("url"):
            return self._dashlet_spec["url"]

        return makeuri_contextless(
            request,
            [
                ("name", self._dashboard_name),
                ("id", self._dashlet_id),
                ("mtime", self._dashboard["mtime"]),
            ],
            filename="dashboard_dashlet.py",
        )

    # TODO: This is specific for the 'url' dashlet type. Move it to that
    # dashlets class once it has been refactored to a class
    def _get_dashlet_url_from_urlfunc(self) -> Optional[str]:
        """Use the URL returned by urlfunc as dashlet URL

        Dashlets using the 'urlfunc' method will dynamically compute
        an url (using HTML context variables at their wish).

        We need to support function pointers to be compatible to old dashboard plugin
        based definitions. The new dashboards use strings to reference functions within
        the global context or functions of a module. An example would be:

        urlfunc: "my_custom_url_rendering_function"

        or within a module:

        urlfunc: "my_module.render_my_url"
        """
        if "urlfunc" not in self._dashlet_spec:
            return None

        urlfunc = self._dashlet_spec["urlfunc"]
        if hasattr(urlfunc, "__call__"):
            return urlfunc()

        if "." in urlfunc:
            module_name, func_name = urlfunc.split(".", 1)
            module = __import__(module_name)
            return module.__dict__[func_name]()

        return globals()[urlfunc]()

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


class VsResultGeneralSettings(TypedDict):
    type: str
    background: bool
    show_title: Union[bool, Literal["transparent"]]
    title: str
    title_url: str
    single_infos: List[str]


def dashlet_vs_general_settings(dashlet_type: Type[Dashlet], single_infos: List[str]):
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


class IFrameDashlet(Dashlet, abc.ABC):
    """Base class for all dashlet using an iframe"""

    @classmethod
    def is_iframe_dashlet(cls) -> bool:
        """Whether or not the dashlet is rendered in an iframe"""
        return True

    def show(self) -> None:
        self._show_initial_iframe_container()

    def reload_on_resize(self) -> bool:
        """Whether or not the page should be reloaded when the dashlet is resized"""
        return self._dashlet_spec.get("reload_on_resize", False)

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
    def page(self):
        settings = json.loads(request.get_str_input_mandatory("settings"))

        try:
            dashlet_type = cast(Type[ABCFigureDashlet], dashlet_registry[settings.get("type")])
        except KeyError:
            raise MKUserError("type", _("The requested element type does not exist."))

        settings = dashlet_vs_general_settings(
            dashlet_type, dashlet_type.single_infos()
        ).value_from_json(settings)

        raw_properties = request.get_str_input_mandatory("properties")
        properties = dashlet_type.vs_parameters().value_from_json(json.loads(raw_properties))
        context = json.loads(request.get_str_input_mandatory("context", "{}"))
        # Inject the infos because the datagenerator is a separate instance to dashlet
        settings["infos"] = dashlet_type.infos()
        response_data = dashlet_type.generate_response_data(properties, context, settings)
        return create_figures_response(response_data)


class ABCFigureDashlet(Dashlet, abc.ABC):
    """Base class for cmk_figures based graphs
    Only contains the dashlet spec, the data generation is handled in the
    DataGenerator classes, to split visualization and data
    """

    @classmethod
    def type_name(cls):
        return "figure_dashlet"

    @classmethod
    def sort_index(cls):
        return 95

    @classmethod
    def initial_refresh_interval(cls):
        return False

    @classmethod
    def initial_size(cls):
        return (56, 40)

    @classmethod
    def infos(cls):
        return ["host", "service"]

    @classmethod
    def single_infos(cls):
        return []

    @classmethod
    def has_context(cls):
        return True

    @property
    def instance_name(self):
        # Note: This introduces the restriction one graph type per dashlet
        return "%s_%s" % (self.type_name(), self._dashlet_id)

    @classmethod
    def vs_parameters(cls) -> ValueSpec:
        return Transform(
            valuespec=Dictionary(
                title=_("Properties"),
                render="form",
                optional_keys=False,
                elements=cls._vs_elements(),
            ),
            forth=cls._transform_vs_forth,
        )

    @classmethod
    def _transform_vs_forth(cls, valuespec_result):
        if "svc_status_display" in valuespec_result:
            # now as code is shared between host and service (svc) dashlet,
            # the `svc_` prefix is removed.
            valuespec_result["status_display"] = valuespec_result.pop("svc_status_display")
        return valuespec_result

    @staticmethod
    def _vs_elements() -> DictionaryElements:
        return []

    @staticmethod
    def generate_response_data(properties, context, settings):
        raise NotImplementedError()

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
            %(instance_name)s.initialize();
            %(instance_name)s.scheduler.set_update_interval(%(update)d);
            %(instance_name)s.scheduler.enable();
            """
            % {
                "type_name": json.dumps(figure_type_name),
                "dashlet_id": self._dashlet_id,
                "instance_name": self.instance_name,
                "div_selector": json.dumps("#%s" % div_id),
                "url": json.dumps(fetch_url),
                "body": json.dumps(post_body),
                "update": self.update_interval,
            }
        )

    def _dashlet_http_variables(self) -> HTTPVariables:
        vs_general_settings = dashlet_vs_general_settings(self.__class__, self.single_infos())
        dashlet_settings = vs_general_settings.value_to_json(self._dashlet_spec)
        dashlet_params = self.vs_parameters()
        assert isinstance(dashlet_params, Transform)  # help mypy
        dashlet_properties = dashlet_params.value_to_json(self._dashlet_spec)

        args: HTTPVariables = []
        args.append(("settings", json.dumps(dashlet_settings)))
        args.append(("context", json.dumps(self.context)))
        args.append(("properties", json.dumps(dashlet_properties)))

        return args


# TODO: Same as in cmk.gui.plugins.views.utils.ViewStore, centralize implementation?
class DashboardStore:
    @classmethod
    @request_memoize()
    def get_instance(cls):
        """Load dashboards only once for each request"""
        return cls()

    def __init__(self):
        self.all = self._load_all()
        self.permitted = self._load_permitted(self.all)

    def _load_all(self) -> Dict[Tuple[UserId, DashboardName], DashboardConfig]:
        """Loads all definitions from disk and returns them"""
        _transform_builtin_dashboards()
        return _transform_dashboards(visuals.load("dashboards", builtin_dashboards))

    def _load_permitted(
        self, all_dashboards: Dict[Tuple[UserId, DashboardName], DashboardConfig]
    ) -> Dict[DashboardName, DashboardConfig]:
        """Returns all defitions that a user is allowed to use"""
        return visuals.available("dashboards", all_dashboards)


def save_all_dashboards() -> None:
    visuals.save("dashboards", get_all_dashboards())


def get_all_dashboards() -> Dict[Tuple[UserId, DashboardName], DashboardConfig]:
    return DashboardStore.get_instance().all


def get_permitted_dashboards() -> Dict[DashboardName, DashboardConfig]:
    return DashboardStore.get_instance().permitted


# During implementation of the dashboard editor and recode of the visuals
# we had serveral different data structures, for example one where the
# views in user dashlets were stored with a context_type instead of the
# "single_info" key, which is the currently correct one.
#
# This code transforms views from user_dashboards.mk which have been
# migrated/created with daily snapshots from 2014-08 till beginning 2014-10.
# FIXME: Can be removed one day. Mark as incompatible change or similar.
# Also this method transforms network topology dashlets to custom url ones
def _transform_dashboards(
    boards: Dict[Tuple[UserId, DashboardName], DashboardConfig]
) -> Dict[Tuple[UserId, DashboardName], DashboardConfig]:
    for dashboard in boards.values():
        visuals.transform_old_visual(dashboard)
        for dashlet in dashboard["dashlets"]:
            visuals.transform_old_visual(dashlet)
            _transform_dashlets_mut(dashlet)

    return boards


def _transform_dashlets_mut(dashlet_spec: DashletConfig) -> DashletConfig:
    # abusing pass by reference to mutate dashlet
    if dashlet_spec["type"] == "view":
        transform_painter_spec(dashlet_spec)

    # ->2014-10
    if dashlet_spec["type"] == "pnpgraph":
        if "service" not in dashlet_spec["single_infos"]:
            dashlet_spec["single_infos"].append("service")
        if "host" not in dashlet_spec["single_infos"]:
            dashlet_spec["single_infos"].append("host")

        # The service context has to be set, otherwise the pnpgraph dashlet would
        # complain about missing context information when displaying host graphs.
        dashlet_spec["context"].setdefault("service", "_HOST_")

    if dashlet_spec["type"] in ["pnpgraph", "custom_graph"]:
        # -> 1.5.0i2
        if "graph_render_options" not in dashlet_spec:
            dashlet_spec["graph_render_options"] = {
                "show_legend": dashlet_spec.pop("show_legend", False),
                "show_service": dashlet_spec.pop("show_service", True),
            }
        # -> 2.0.0b6
        transform_graph_render_options(dashlet_spec["graph_render_options"])
        dashlet_spec["graph_render_options"].pop("show_title", None)
        # title_format is not used in Dashlets (Custom tiltle instead, field 'title')
        dashlet_spec["graph_render_options"].pop("title_format", None)

    if dashlet_spec["type"] == "network_topology":
        # -> 2.0.0i Removed network topology dashlet type
        transform_topology_dashlet(dashlet_spec)

    if dashlet_spec["type"] in ["notifications_bar_chart", "alerts_bar_chart"]:
        # -> v2.0.0b6 introduced the different render modes
        _transform_event_bar_chart_dashlet(dashlet_spec)

    return dashlet_spec


def _transform_event_bar_chart_dashlet(dashlet_spec: DashletConfig):
    if "render_mode" not in dashlet_spec:
        dashlet_spec["render_mode"] = (
            "bar_chart",
            {
                "time_range": dashlet_spec.pop("time_range", "d0"),
                "time_resolution": dashlet_spec.pop("time_resolution", "h"),
            },
        )


def transform_topology_dashlet(
    dashlet_spec: DashletConfig, filter_group: str = ""
) -> DashletConfig:
    site_id = dashlet_spec["context"].get("site", omd_site())

    dashlet_spec.update(
        {
            "type": "url",
            "title": _("Network topology of site %s") % site_id,
            "url": "../nagvis/frontend/nagvis-js/index.php?mod=Map&header_template="
            "on-demand-filter&header_menu=1&label_show=1&sources=automap&act=view"
            "&backend_id=%s&render_mode=undirected&url_target=main&filter_group=%s"
            % (site_id, filter_group),
            "show_in_iframe": True,
        }
    )

    return dashlet_spec


def transform_stats_dashlet(dashlet_spec: DashletConfig) -> DashletConfig:
    # Stats dashlets in version 2.0 are no longer updated through the dashboard scheduler
    dashlet_spec.pop("refresh", None)
    return dashlet_spec


def transform_timerange_dashlet(dashlet_spec: DashletConfig) -> DashletConfig:
    dashlet_spec["timerange"] = {
        "0": "4h",
        "1": "25h",
        "2": "8d",
        "3": "35d",
        "4": "400d",
    }.get(dashlet_spec["timerange"], dashlet_spec["timerange"])
    return dashlet_spec


# be compatible to old definitions, where even internal dashlets were
# referenced by url, e.g. dashboard['url'] = 'hoststats.py'
# FIXME: can be removed one day. Mark as incompatible change or similar.
def _transform_builtin_dashboards() -> None:
    for name, dashboard in builtin_dashboards.items():
        # Do not transform dashboards which are already in the new format
        if "context" in dashboard:
            continue

        # Transform the dashlets
        for nr, dashlet in enumerate(dashboard["dashlets"]):
            dashlet.setdefault("show_title", True)

            if dashlet.get("url", "").startswith("dashlet_hoststats") or dashlet.get(
                "url", ""
            ).startswith("dashlet_servicestats"):

                # hoststats and servicestats
                dashlet["type"] = dashlet["url"][8:].split(".", 1)[0]

                if "?" in dashlet["url"]:
                    # Transform old parameters:
                    # wato_folder
                    # host_contact_group
                    # service_contact_group
                    paramstr = dashlet["url"].split("?", 1)[1]
                    dashlet["context"] = {}
                    for key, val in [p.split("=", 1) for p in paramstr.split("&")]:
                        if key == "host_contact_group":
                            dashlet["context"]["opthost_contactgroup"] = {
                                "neg_opthost_contact_group": "",
                                "opthost_contact_group": val,
                            }
                        elif key == "service_contact_group":
                            dashlet["context"]["optservice_contactgroup"] = {
                                "neg_optservice_contact_group": "",
                                "optservice_contact_group": val,
                            }
                        elif key == "wato_folder":
                            dashlet["context"]["wato_folder"] = {
                                "wato_folder": val,
                            }

                del dashlet["url"]

            elif dashlet.get("urlfunc") and not isinstance(dashlet["urlfunc"], str):
                raise MKGeneralException(
                    _(
                        "Unable to transform dashlet %d of dashboard %s: "
                        'the dashlet is using "urlfunc" which can not be '
                        "converted automatically."
                    )
                    % (nr, name)
                )

            elif dashlet.get("url", "") != "" or dashlet.get("urlfunc") or dashlet.get("iframe"):
                # Normal URL based dashlet
                dashlet["type"] = "url"

                if dashlet.get("iframe"):
                    dashlet["url"] = dashlet["iframe"]
                    del dashlet["iframe"]

            elif dashlet.get("view", "") != "":
                # Transform views
                # There might be more than the name in the view definition
                view_name = dashlet["view"].split("&")[0]

                # Copy the view definition into the dashlet
                copy_view_into_dashlet(dashlet, nr, view_name, load_from_all_views=True)
                del dashlet["view"]

            else:
                raise MKGeneralException(
                    _(
                        "Unable to transform dashlet %d of dashboard %s. "
                        "You will need to migrate it on your own. Definition: %r"
                    )
                    % (nr, name, escaping.escape_attribute(dashlet))
                )

            dashlet.setdefault("context", {})
            dashlet.setdefault("single_infos", [])

        # the modification time of builtin dashboards can not be checked as on user specific
        # dashboards. Set it to 0 to disable the modification chech.
        dashboard.setdefault("mtime", 0)

        dashboard.setdefault("show_title", True)
        if dashboard["title"] is None:
            dashboard["title"] = _("No title")
            dashboard["show_title"] = False

        dashboard.setdefault("single_infos", [])
        dashboard.setdefault("context", {})
        dashboard.setdefault("topic", _("Overview"))
        dashboard.setdefault("description", dashboard.get("title", ""))


def copy_view_into_dashlet(
    dashlet: DashletConfig,
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
        view = None
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
    dashlet.update(view)
    if add_context:
        dashlet["context"].update(add_context)

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


def host_table_query(properties, context, column_generator):
    return _table_query(properties, context, column_generator, "hosts", ["host"])


def service_table_query(properties, context, column_generator):
    return _table_query(properties, context, column_generator, "services", ["host", "service"])


def _table_query(
    properties, context, column_generator, table: str, infos: List[str]
) -> Tuple[List[str], LivestatusResponse]:
    filter_headers, only_sites = visuals.get_filter_headers(table, infos, context)
    columns = column_generator(properties, context)

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

    return ["site"] + columns, rows


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


def create_data_for_single_metric(
    properties,
    context: VisualContext,
    column_generator: Callable[[Any, VisualContext], List[str]],
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, TranslatedMetric, Dict[str, LivestatusColumn]]]]:
    # TODO: should return live value and historic values as two different elements, for better typing support.
    columns, data_rows = service_table_query(properties, context, column_generator)

    data = []
    used_metrics = []

    for idx, row in enumerate(data_rows):
        d_row = dict(zip(columns, row))
        translated_metrics = translate_perf_data(
            d_row["service_perf_data"], d_row["service_check_command"]
        )
        metric = translated_metrics.get(properties["metric"])

        if metric is None:
            continue

        series = merge_multicol(d_row, columns, properties)
        host = d_row["host_name"]
        row_id = "row_%d" % idx

        # Historic values
        for ts, elem in series.time_data_pairs():
            if elem:
                data.append(
                    {
                        "tag": row_id,
                        "timestamp": ts,
                        "value": elem,
                        "label": host,
                    }
                )

        # Live value
        data.append(
            {
                "tag": row_id,
                "last_value": True,
                "timestamp": int(time.time()),
                "value": metric["value"],
                "label": host,
                "url": create_service_view_url(d_row),
            }
        )

        used_metrics.append((row_id, metric, d_row))

    return data, used_metrics


def dashboard_breadcrumb(name: str, board: DashboardConfig, title: str) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(
        mega_menu_registry.menu_monitoring(), PagetypeTopics.get_topic(board["topic"])
    )
    breadcrumb.append(BreadcrumbItem(title, makeuri_contextless(request, [("name", name)])))
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
        # TODO: remove underscore from _state_names and remove this method
        # when https://github.com/python/mypy/pull/10548 is released
        return self._state_names(row)  # type: ignore


class ServiceStateFormatter(StateFormatter):
    def __init__(self, message_template: str = "{}") -> None:
        super().__init__(
            css="svcstate state{}",
            _state_names=service_state_short,
            message_template=message_template,
        )
        self.css = "svcstate state{}"
        # TODO: see comment in StateFormatter.state_names
        self._state_names = service_state_short  # type: ignore
        self.message_template = message_template


def state_map(conf: Optional[Tuple[str, str]], row: Row, formatter: StateFormatter):
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
