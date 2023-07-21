#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import copy
import json
import os
import pickle
import re
import sys
import traceback
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import suppress
from itertools import chain
from pathlib import Path
from typing import Any, cast, Final, Generic, get_args, TypeVar

from pydantic import BaseModel

from livestatus import LivestatusTestingError

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.packaging import PackageName
from cmk.utils.user import UserId

import cmk.gui.forms as forms
import cmk.gui.pagetypes as pagetypes
import cmk.gui.query_filters as query_filters
import cmk.gui.userdb as userdb
import cmk.gui.utils as utils
from cmk.gui import hooks
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.config import active_config, default_authorized_builtin_role_ids
from cmk.gui.ctx_stack import g
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import HTMLContent
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.log import logger
from cmk.gui.logged_in import save_user_file, user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    doc_reference_to_page_menu,
    make_javascript_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuTopic,
)
from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import declare_permission, permission_registry
from cmk.gui.plugins.visuals.utils import (
    active_filter_flag,
    collect_filters,
    Filter,
    filter_registry,
    filters_allowed_for_info,
    filters_allowed_for_infos,
    get_livestatus_filter_headers,
    get_only_sites_from_context,
    visual_info_registry,
    visual_type_registry,
    VisualType,
)
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import (
    FilterHTTPVariables,
    FilterName,
    HTTPVariables,
    Icon,
    InfoName,
    PermissionName,
    SingleInfos,
    ViewSpec,
    Visual,
    VisualContext,
    VisualName,
    VisualTypeName,
)
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import is_user_with_publish_permissions, user_may
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    file_name_and_query_vars_from_url,
    make_confirm_delete_link,
    make_confirm_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
    urlencode,
)
from cmk.gui.validate import validate_id
from cmk.gui.valuespec import (
    ABCPageListOfMultipleGetChoice,
    CascadingDropdown,
    Checkbox,
    DEF_VALUE,
    Dictionary,
    DropdownChoice,
    DualListChoice,
    FixedValue,
    GroupedListOfMultipleChoices,
    IconSelector,
    Integer,
    JSONValue,
    ListOfMultiple,
    ListOfMultipleChoiceGroup,
    TextAreaUnicode,
    TextInput,
    Transform,
    ValueSpec,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
    ValueSpecValidateFunc,
)

from ._breadcrumb import visual_page_breadcrumb as visual_page_breadcrumb
from ._page_create_visual import page_create_visual as page_create_visual
from ._page_create_visual import SingleInfoSelection as SingleInfoSelection
from ._page_list import page_list as page_list
from ._permissions import declare_visual_permissions as declare_visual_permissions
from ._store import available as available
from ._store import declare_custom_permissions as declare_custom_permissions
from ._store import declare_packaged_visuals_permissions as declare_packaged_visuals_permissions
from ._store import delete_local_file, get_installed_packages
from ._store import get_permissioned_visual as get_permissioned_visual
from ._store import load as load
from ._store import load_visuals_of_a_user as load_visuals_of_a_user
from ._store import local_file_exists, move_visual_to_local
from ._store import save as save
from ._store import TVisual as TVisual


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("ajax_visual_filter_list_get_choice")(
        PageAjaxVisualFilterListGetChoice
    )
    page_registry.register_page_handler("ajax_popup_add_visual", ajax_popup_add)
    page_registry.register_page_handler("ajax_add_visual", ajax_add_visual)


#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("visuals", globals())


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.plugins.visuals as api_module
    import cmk.gui.plugins.visuals.utils as plugin_utils

    for name in (
        "Filter",
        "filter_registry",
        "FilterOption",
        "FilterTime",
        "get_only_sites_from_context",
        "visual_info_registry",
        "visual_type_registry",
        "VisualInfo",
        "VisualType",
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name]


# .
#   .--Edit Visual---------------------------------------------------------.
#   |           _____    _ _ _    __     ___                 _             |
#   |          | ____|__| (_) |_  \ \   / (_)___ _   _  __ _| |            |
#   |          |  _| / _` | | __|  \ \ / /| / __| | | |/ _` | |            |
#   |          | |__| (_| | | |_    \ V / | \__ \ |_| | (_| | |            |
#   |          |_____\__,_|_|\__|    \_/  |_|___/\__,_|\__,_|_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Edit global settings of the visual                                   |
#   '----------------------------------------------------------------------'


def get_context_specs(
    single_infos: Sequence[InfoName], info_keys: Sequence[InfoName]
) -> list[tuple[InfoName, Transform[dict] | VisualFilterList]]:
    single_info_keys = [key for key in info_keys if key in single_infos]
    multi_info_keys = [key for key in info_keys if key not in single_info_keys]

    def host_service_lead(val: tuple[InfoName, Transform[dict] | VisualFilterList]) -> int:
        # Sort is stable in python, thus only prioritize host>service>rest
        if val[0] == "host":
            return 0
        if val[0] == "service":
            return 1
        return 2

    # single infos first, the rest afterwards
    context_specs: list[tuple[InfoName, Transform[dict] | VisualFilterList]] = [
        (info_key, _visual_spec_single(info_key)) for info_key in single_info_keys
    ] + [
        (info_key, spec)
        for info_key in multi_info_keys
        for spec in [_visual_spec_multi(info_key)]
        if spec is not None
    ]

    return sorted(context_specs, key=host_service_lead)


def _visual_spec_single(info_key: InfoName) -> Transform[dict]:
    # VisualInfos have a single_spec, which might declare multiple filters.
    # In this case each spec is as filter value and it is typed(at the moment only Integer & TextInput).
    # Filters at the moment, due to use of url_vars, are string only.
    # At the moment single_info_spec relation to filters is:
    #     for all (i): info.single_spec[i][0]==filter.ident==filter.htmlvars[0]

    # This _visual_spec_single stores direct into the VisualContext, thus it needs to dissosiate
    # the single_spec into separate filters. This transformations are the equivalent of flattening
    # the values into the url, but now they preserve the VisualContext type.

    # In both cases unused keys need to be removed otherwise empty values proliferate
    # either they are saved or they corrupt the VisualContext during merges.

    def from_valuespec(
        values: dict[str, str | int], single_spec: list[tuple[FilterName, ValueSpec]]
    ) -> VisualContext:
        return {
            ident: {ident: str(value)}
            for ident, _vs in single_spec
            for value in [values.get(ident)]
            if value
        }

    def to_valuespec(
        context: VisualContext, single_spec: list[tuple[FilterName, ValueSpec]]
    ) -> dict[str, str | int]:
        return {
            ident: value
            for ident, vs in single_spec
            for value in [context.get(ident, {}).get(ident)]
            if value
        }

    info = visual_info_registry[info_key]()

    return Transform(
        valuespec=Dictionary(
            title=info.title,
            form_isopen=True,
            optional_keys=True,
            elements=info.single_spec,
        ),
        from_valuespec=lambda values: from_valuespec(values, info.single_spec),
        to_valuespec=lambda context: to_valuespec(context, info.single_spec),
    )


def _visual_spec_multi(info_key: InfoName) -> VisualFilterList | None:
    info = visual_info_registry[info_key]()
    filter_list = VisualFilterList([info_key], title=info.title)
    filter_names = filter_list.filter_names()
    # Skip infos which have no filters available
    return filter_list if filter_names else None


def process_context_specs(
    context_specs: list[tuple[InfoName, Transform[dict] | VisualFilterList]]
) -> VisualContext:
    context: dict[str, Any] = {}
    for info_key, spec in context_specs:
        ident = "context_" + info_key

        attrs = spec.from_html_vars(ident)
        spec.validate_value(dict(attrs), ident)
        context.update(attrs)
    return context


def render_context_specs(
    context: VisualContext,
    context_specs: list[tuple[InfoName, Transform[dict] | VisualFilterList]],
    isopen: bool = True,
    help_text: str | HTML | None = None,
) -> None:
    if not context_specs:
        return

    forms.header(
        _("Context / Search Filters"),
        isopen=isopen,
        show_more_toggle=any(vs.has_show_more() for _title, vs in context_specs if vs is not None),
        help_text=help_text,
    )
    # Trick: the field "context" contains a dictionary with
    # all filter settings, from which the value spec will automatically
    # extract those that it needs.
    for info_key, spec in context_specs:
        forms.section(
            spec.title(),
            is_show_more=spec.has_show_more()
            if isinstance(spec, Transform)
            else all(flt.is_show_more for _title, flt in spec.filter_items() if flt is not None),
        )
        ident = "context_" + info_key
        spec.render_input(ident, context)


def _vs_general(
    single_infos: SingleInfos,
    default_id: str,
    visual_type: VisualType,
    visibility_elements: list[tuple[str, ValueSpec]],
    all_visuals: dict[tuple[UserId, VisualName], TVisual],
    mode: str,
    what: VisualTypeName,
) -> Dictionary:
    return Dictionary(
        title=_("General Properties"),
        render="form",
        optional_keys=False,
        show_more_keys=["description", "add_context_to_title", "sort_index", "is_show_more"],
        elements=[
            single_infos_spec(single_infos),
            (
                "name",
                TextInput(
                    title=_("Unique ID"),
                    help=_(
                        "The ID will be used in URLs that point to a view, e.g. "
                        "<tt>view.py?view_name=<b>myview</b></tt>. It will also be used "
                        "internally for identifying a view. You can create several views "
                        "with the same title but only one per view name. If you create a "
                        "view that has the same view name as a builtin view, then your "
                        "view will override that (shadowing it)."
                    ),
                    regex="^[a-zA-Z0-9_]+$",
                    regex_error=_(
                        "The name of the view may only contain letters, digits and underscores."
                    ),
                    size=50,
                    allow_empty=False,
                    default_value=default_id,
                ),
            ),
            ("title", TextInput(title=_("Title") + "<sup>*</sup>", size=50, allow_empty=False)),
            (
                "description",
                TextAreaUnicode(
                    title=_("Description") + "<sup>*</sup>",
                    rows=4,
                    cols=50,
                ),
            ),
            (
                "add_context_to_title",
                Checkbox(
                    title=_("Context information"),
                    label=_("Add context information to title"),
                    help=_(
                        "Whether or not additional information from the page context "
                        "(filters) should be added to the title given above."
                    ),
                ),
            ),
            (
                "topic",
                DropdownChoice(
                    title=_("Topic in ’Monitor' menu"),
                    default_value="my_workplace",
                    help=_(
                        "Dashboards will be visible in the ‘Monitor’ main menu. "
                        "With this option, you can select in which section of the menu this "
                        "dashboard should be accessible. If you want to define a new "
                        "topic name you can do this <a href='%s'>here</a>."
                    )
                    % "pagetype_topics.py",
                    choices=pagetypes.PagetypeTopics.choices(),
                ),
            ),
            (
                "sort_index",
                Integer(
                    title=_("Sort index"),
                    default_value=99,
                    help=_(
                        "You can customize the order of the %s by changing "
                        "this number. Lower numbers will be sorted first. "
                        "Topics with the same number will be sorted alphabetically."
                    )
                    % visual_type.title,
                ),
            ),
            (
                "is_show_more",
                Checkbox(
                    title=_("Show more"),
                    label=_("Only show the %s if show more is active") % visual_type.title,
                    help=_(
                        "The navigation allows to hide items based on a show "
                        "less / show more toggle. You can specify here whether or "
                        "not this %s should only be shown with show more %s."
                    )
                    % (visual_type.title, visual_type.title),
                ),
            ),
            (
                "icon",
                IconSelector(
                    title=_("Icon"),
                    help=_(
                        "This selection is only relevant if under 'User' "
                        "-> 'Edit Profile' -> 'Mega menue icons' you have selected "
                        "the options 'Per Entry'. If this is the case, you "
                        "select here the icon that will be placed next to your "
                        "Dashboard’s name in the Monitoring menu. You can only "
                        "select one icon (the colored icon) or one icon that is "
                        "complemented with an additional symbol."
                    ),
                ),
            ),
            (
                "visibility",
                Dictionary(
                    title=_("Visibility"),
                    elements=visibility_elements,
                ),
            ),
        ],
        validate=validate_id(
            mode,
            {k: v for k, v in available(what, all_visuals).items() if v["owner"] == user.id},
        ),
    )


def page_edit_visual(  # type: ignore[no-untyped-def] # pylint: disable=too-many-branches
    what: VisualTypeName,
    all_visuals: dict[tuple[UserId, VisualName], TVisual],
    custom_field_handler=None,
    create_handler=None,
    info_handler=None,
    sub_pages: pagetypes.SubPagesSpec | None = None,
    help_text_context: str | HTML | None = None,
) -> None:
    if sub_pages is None:
        sub_pages = []

    visual_type = visual_type_registry[what]()
    if not user.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % visual_type.plural_title)
    visual: dict[str, Any] = {
        "link_from": {},
        "context": {},
    }

    mode = request.get_str_input_mandatory("mode", "edit")
    visualname = request.get_str_input_mandatory("load_name", "")
    oldname = visualname
    owner_user_id = user.id

    def _get_visual(owner_id, mode):
        if visual := all_visuals.get((owner_id, visualname)):
            return visual
        if mode == "clone":
            return _get_visual("", "builtins")
        raise MKUserError(mode, _("The %s does not exist.") % visual_type.title)

    back_url = request.get_url_input("back", "edit_%s.py" % what)

    if visualname:
        owner_id = request.get_validated_type_input_mandatory(UserId, "owner", user.id)
        visual = _get_visual(owner_id, mode)

        if mode == "edit" and owner_id != "":  # editing builtins requires copy
            if owner_id != user.id:
                if not user.may("general.edit_foreign_%s" % what):
                    raise MKAuthException(
                        _("You are not allowed to edit foreign %s.") % visual_type.plural_title
                    )
            owner_user_id = owner_id
            title = _("Edit %s") % visual_type.title
        elif mode == "export":
            move_visual_to_local(
                request.get_str_input_mandatory("load_name"),
                request.get_validated_type_input_mandatory(UserId, "owner", user.id),
                all_visuals,
                what,
            )
            raise HTTPRedirect(back_url)
        elif mode == "delete":
            delete_local_file(what, visualname)
            raise HTTPRedirect(back_url)
        else:  # clone explicit or edit from builtin that needs copy
            title = _("Clone %s") % visual_type.title
            visual = copy.deepcopy(visual)
            visual["public"] = False

            # Name conflict -> try new names
            newname, n = visualname, 0
            while (owner_user_id, newname) in all_visuals:
                n += 1
                newname = visualname + "_clone%d" % n
            visual["name"] = newname
            visualname = newname
            oldname = ""  # Prevent renaming
            if owner_id == owner_user_id:
                visual["title"] += _(" (Copy)")

        single_infos = visual["single_infos"]

    else:
        title = _("Create %s") % visual_type.title
        mode = "create"
        single_infos = []
        single_infos_raw = request.var("single_infos")
        if single_infos_raw:
            single_infos = single_infos_raw.split(",")
            for key in single_infos:
                if key not in visual_info_registry:
                    raise MKUserError("single_infos", _("The info %s does not exist.") % key)
        visual["single_infos"] = single_infos

    breadcrumb = visual_page_breadcrumb(what, title, mode)
    page_menu = pagetypes.make_edit_form_page_menu(
        breadcrumb,
        dropdown_name=what[:-1],
        mode=mode,
        type_title=visual_type.title,
        type_title_plural=visual_type.plural_title,
        ident_attr_name=visual_type.ident_attr,
        sub_pages=sub_pages,
        form_name="visual",
        visualname=visualname,
    )
    make_header(html, title, breadcrumb, page_menu)

    # A few checkboxes concerning the visibility of the visual. These will
    # appear as boolean-keys directly in the visual dict, but encapsulated
    # in a list choice in the value spec.
    visibility_elements: list[tuple[str, ValueSpec]] = [
        (
            "hidden",
            FixedValue(
                value=True,
                title=_("Hide this %s in the monitor menu") % visual_type.title,
                totext="",
            ),
        ),
        (
            "hidebutton",
            FixedValue(
                value=True,
                title=_("Hide this %s in dropdown menus") % visual_type.title,
                totext="",
            ),
        ),
    ]

    if is_user_with_publish_permissions("visual", user.id, what):
        visibility_elements.append(
            (
                "public",
                pagetypes.PublishTo(
                    publish_all=user.may("general.publish_" + what),
                    publish_groups=user.may("general.publish_" + what + "_to_groups"),
                    publish_sites=user.may("general.publish_" + what + "_to_sites"),
                    type_title=visual_type.title,
                    with_foreign_groups=user.may("general.publish_" + what + "_to_foreign_groups"),
                ),
            )
        )
    else:
        visibility_elements.append(
            (
                "public",
                pagetypes.vs_no_permission_to_publish(
                    type_title=what[:-1],
                    title=_("Make this %s available for other users") % what[:-1],
                ),
            )
        )

    vs_general = _vs_general(
        single_infos,
        unique_default_name_suggestion(
            what[:-1],
            (visual["name"] for visual in all_visuals.values()),
        ),
        visual_type,
        visibility_elements,
        all_visuals,
        mode,
        what,
    )
    context_specs = get_context_specs(
        visual["single_infos"],
        info_handler(visual) if info_handler else list(visual_info_registry.keys()),
    )

    # handle case of save or try or press on search button
    save_and_go = None
    for nr, (title, pagename, _icon) in enumerate(sub_pages):
        if request.var("save%d" % nr):
            save_and_go = pagename

    if save_and_go or request.var("_save") or request.var("save_and_view") or request.var("search"):
        try:
            general_properties = vs_general.from_html_vars("general")

            vs_general.validate_value(general_properties, "general")

            if not general_properties["topic"]:
                general_properties["topic"] = "other"

            old_visual = visual
            # TODO: Currently not editable, but keep settings
            visual = {"link_from": old_visual["link_from"]}

            # Important for saving
            visual["packaged"] = False

            # The dict of the value spec does not match exactly the dict
            # of the visual. We take over some keys...
            for key in [
                "single_infos",
                "name",
                "title",
                "topic",
                "sort_index",
                "is_show_more",
                "description",
                "icon",
                "add_context_to_title",
            ]:
                visual[key] = general_properties[key]

            # ...and import the visibility flags directly into the visual
            for key, _value in visibility_elements:
                visual[key] = general_properties["visibility"].get(key, False)

            if not is_user_with_publish_permissions("visual", user.id, what):
                visual["public"] = False

            if create_handler:
                visual = create_handler(old_visual, visual)

            visual["context"] = process_context_specs(context_specs)

            if request.var("_save") or request.var("save_and_view") or save_and_go:
                if save_and_go:
                    back_url = makeuri_contextless(
                        request,
                        [(visual_type.ident_attr, visual["name"])],
                        filename=save_and_go + ".py",
                    )

                if request.var("save_and_view"):
                    back_vars: HTTPVariables = []
                    back_url_from_vars = request.var("back")
                    if back_url_from_vars:
                        _file_name, query_vars = file_name_and_query_vars_from_url(
                            back_url_from_vars
                        )
                        back_vars = [(varname, value[0]) for varname, value in query_vars.items()]
                    visual_name_var: tuple[str, str] = (visual_type.ident_attr, visual["name"])
                    if visual_name_var not in back_vars:
                        back_vars.append(visual_name_var)

                    back_url = makeuri_contextless(
                        request,
                        back_vars,
                        filename=visual_type.show_url,
                    )

                if transactions.check_transaction():
                    assert owner_user_id is not None
                    # Since we have no way to parse the raw dictionary and Dictionary is also not
                    # typable, we need to hope here that page_dict fits with TVisual. On the mission to at
                    # least add some typing here, we take this shortcut for now. There are way
                    # bigger problems in this class hierarchy than the edit dialog we should solve
                    # first.
                    all_visuals[(owner_user_id, visual["name"])] = cast(TVisual, visual)
                    # Handle renaming of visuals
                    if oldname and oldname != visual["name"]:
                        # -> delete old entry
                        if (owner_user_id, oldname) in all_visuals:
                            del all_visuals[(owner_user_id, oldname)]
                        # -> change visual_name in back parameter
                        if back_url:
                            varstring = visual_type.ident_attr + "="
                            back_url = back_url.replace(
                                varstring + oldname, varstring + visual["name"]
                            )
                    save(what, all_visuals, owner_user_id)

                if not request.var("save_and_view"):
                    flash(_("Your %s has been saved.") % visual_type.title)
                html.reload_whole_page(back_url)
                html.footer()
                return

        except MKUserError as e:
            html.user_error(e)

    html.begin_form("visual", method="POST")
    html.hidden_field("back", back_url)
    html.hidden_field("mode", mode)
    if request.has_var("owner"):
        html.hidden_field("owner", request.var("owner"))
    html.hidden_field("load_name", oldname)  # safe old name in case user changes it

    # FIXME: Hier werden die Flags aus visibility nicht korrekt geladen. Wäre es nicht besser,
    # diese in einem Unter-Dict zu lassen, anstatt diese extra umzukopieren?
    visib = {}
    for key, _vs in visibility_elements:
        if visual.get(key):
            visib[key] = visual[key]
    visual["visibility"] = visib

    visual["topic"] = visual.get("topic") or "other"  # default to "other" (in case of empty string)
    vs_general.render_input("general", visual)

    if custom_field_handler and custom_field_handler.__name__ != "dashboard_fields_handler":
        custom_field_handler(visual)

    render_context_specs(
        # During view configuration: if a MKUserError is raised BEFORE the visual context is set
        # via 'visual["context"] = process_context_specs(context_specs)' from above then we get a
        # KeyError here and the whole configuration is lost and has to be started from scratch.
        # Example: If no column is choosen.
        visual.get("context", {}),
        context_specs,
        isopen=what != "dashboards",
        help_text=help_text_context,
    )

    if custom_field_handler and custom_field_handler.__name__ == "dashboard_fields_handler":
        custom_field_handler(visual)

    forms.end()
    html.show_localization_hint()

    html.hidden_fields()
    html.end_form()
    html.footer()


# .
#   .--Filters-------------------------------------------------------------.
#   |                     _____ _ _ _                                      |
#   |                    |  ___(_) | |_ ___ _ __ ___                       |
#   |                    | |_  | | | __/ _ \ '__/ __|                      |
#   |                    |  _| | | | ||  __/ |  \__ \                      |
#   |                    |_|   |_|_|\__\___|_|  |___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


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
            html.write_html(HTML(output_funnel.drain()))
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
        html.write_text(_("This filter cannot be displayed"))
    html.close_div()
    html.close_div()


def get_filter(name: str) -> Filter:
    """Returns the filter object identified by the given name
    Raises a KeyError in case a not existing filter is requested."""
    return filter_registry[name]


# For all single_infos which are configured for a view which datasource
# does not provide these infos, try to match the keys of the single_info
# attributes to a filter which can then be used to filter the data of
# the available infos.
# This is needed to make the "hostgroup" single_info possible on datasources
# which do not have the "hostgroup" info, but the "host" info. This
# is some kind of filter translation between a filter of the "hostgroup" info
# and the "hosts" info.
def get_link_filter_names(
    single_infos: SingleInfos,
    info_keys: SingleInfos,
    link_filters: dict[FilterName, FilterName],
) -> Iterator[tuple[FilterName, FilterName]]:
    for info_key in single_infos:
        if info_key not in info_keys:
            for key in info_params(info_key):
                if key in link_filters:
                    yield key, link_filters[key]


def filters_of_visual(
    visual: Visual,
    info_keys: SingleInfos,
    link_filters: dict[FilterName, FilterName] | None = None,
) -> list[Filter]:
    """Collects all filters to be used for the given visual"""
    if link_filters is None:
        link_filters = {}

    filters: dict[FilterName, Filter] = {}
    for info_key in info_keys:
        if info_key in visual["single_infos"]:
            for key in info_params(info_key):
                filters[key] = get_filter(key)
            continue

        for key, val in visual["context"].items():
            if isinstance(val, dict):  # this is a real filter
                try:
                    filters[key] = get_filter(key)
                except KeyError:
                    pass  # Silently ignore not existing filters

    # See get_link_filter_names() comment for details
    for key, dst_key in get_link_filter_names(visual["single_infos"], info_keys, link_filters):
        filters[dst_key] = get_filter(dst_key)

    # add ubiquitary_filters that are possible for these infos
    for fn in get_ubiquitary_filters():
        # Disable 'wato_folder' filter, if Setup is disabled or there is a single host view
        filter_ = get_filter(fn)

        if fn == "wato_folder" and (not filter_.available() or "host" in visual["single_infos"]):
            continue
        if not filter_.info or filter_.info in info_keys:
            filters[fn] = filter_

    return list(filters.values())


# TODO: Cleanup this special case
def get_ubiquitary_filters() -> list[FilterName]:
    return ["wato_folder"]


# Reduces the list of the visuals used filters. The result are the ones
# which are really presented to the user later.
# For the moment we only remove the single context filters which have a
# hard coded default value which is treated as enforced value.
def visible_filters_of_visual(visual: Visual, use_filters: list[Filter]) -> list[Filter]:
    show_filters = []

    single_keys = get_single_info_keys(visual["single_infos"])

    for f in use_filters:
        if f.ident not in single_keys or not visual["context"].get(f.ident):
            show_filters.append(f)

    return show_filters


def context_to_uri_vars(context: VisualContext) -> list[tuple[str, str]]:
    """Produce key/value tuples for HTTP variables from the visual context"""
    return list(chain.from_iterable(filter_vars.items() for filter_vars in context.values()))


# Vice versa: find all filters that belong to the current URI variables
# and create a context dictionary from that.
def get_context_from_uri_vars(only_infos: SingleInfos | None = None) -> VisualContext:
    context = {}
    for filter_name, filter_object in filter_registry.items():
        if only_infos is not None and filter_object.info not in only_infos:
            continue  # Skip filters related to not relevant infos

        this_filter_vars = {}
        for varname in filter_object.htmlvars:
            if not request.has_var(varname):
                continue  # Variable to set in environment

            filter_value = request.get_str_input_mandatory(varname)
            if not filter_value:
                continue

            this_filter_vars[varname] = filter_value

        if this_filter_vars:
            context[filter_name] = this_filter_vars

    return context


def get_merged_context(*contexts: VisualContext) -> VisualContext:
    """Merges multiple filter contexts to a single one

    The last context that sets a filter wins. The intended order is to provide contexts in
    "descending order", e.g. like this for dashboards:

    1. URL context
    2. Dashboard context
    3. Dashlet context
    """
    return {key: value for context in contexts for key, value in context.items()}


# Compute Livestatus-Filters based on a given context. Returns
# the only_sites list and a string with the filter headers
# TODO: Untangle only_sites and filter headers
# TODO: Reduce redundancies with filters_of_visual()
def get_filter_headers(table, infos, context: VisualContext):  # type: ignore[no-untyped-def]
    filter_headers = "".join(get_livestatus_filter_headers(context, collect_filters(infos)))
    return filter_headers, get_only_sites_from_context(context)


# .
#   .--ValueSpecs----------------------------------------------------------.
#   |        __     __    _            ____                                |
#   |        \ \   / /_ _| |_   _  ___/ ___| _ __   ___  ___ ___           |
#   |         \ \ / / _` | | | | |/ _ \___ \| '_ \ / _ \/ __/ __|          |
#   |          \ V / (_| | | |_| |  __/___) | |_) |  __/ (__\__ \          |
#   |           \_/ \__,_|_|\__,_|\___|____/| .__/ \___|\___|___/          |
#   |                                       |_|                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def FilterChoices(  # type: ignore[no-untyped-def] # pylint: disable=redefined-builtin
    infos: SingleInfos, title: str, help: str
):
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


class VisualFilterList(ListOfMultiple):
    """Implements a list of available filters for the given infos. By default no
    filter is selected. The user may select a filter to be activated, then the
    filter is rendered and the user can provide a default value.
    """

    @classmethod
    def get_choices(cls, info: str) -> Sequence[tuple[str, VisualFilter]]:
        return sorted(
            cls._get_filter_specs(info), key=lambda x: (x[1]._filter.sort_index, x[1].title())
        )

    @classmethod
    def _get_filter_specs(cls, info: str) -> Iterator[tuple[str, VisualFilter]]:
        for fname, filter_ in filters_allowed_for_info(info):
            yield fname, VisualFilter(name=fname, title=filter_.title)

    def __init__(self, info_list: SingleInfos, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._filters = filters_allowed_for_infos(info_list)

        kwargs.setdefault("title", _("Filters"))
        kwargs.setdefault("add_label", _("Add filter"))
        kwargs.setdefault("del_label", _("Remove filter"))
        kwargs["delete_style"] = "filter"

        grouped: GroupedListOfMultipleChoices = [
            ListOfMultipleChoiceGroup(
                title=visual_info_registry[info]().title, choices=self.get_choices(info)
            )
            for info in info_list
        ]
        super().__init__(
            choices=grouped,
            choice_page_name="ajax_visual_filter_list_get_choice",
            page_request_vars={
                "infos": info_list,
            },
            **kwargs,
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
            html.a(
                group.title,
                href="",
                class_="filter_group_title",
                onclick="cmk.page_menu.toggle_filter_group_display(this.nextSibling)",
            )

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
            "cmk.valuespecs.listofmultiple_init(%s, %s);"
            % (json.dumps(varprefix), json.dumps(filters_applied))
        )
        html.javascript("cmk.utils.add_simplebar_scrollbar(%s);" % json.dumps(filter_list_id))


def active_context_from_request(infos: SingleInfos, context: VisualContext) -> VisualContext:
    vs_filterlist = VisualFilterListWithAddPopup(info_list=infos)
    if request.has_var("_active"):
        return vs_filterlist.from_html_vars("")

    # Test if filters are in url and rescostruct them. This is because we
    # contruct crosslinks manually without the filter menu.
    # We must merge with the view context as many views have defaults, which
    # are not included in the crosslink.
    if flag := active_filter_flag(set(vs_filterlist._filters.keys()), request.itervars()):
        with request.stashed_vars():
            request.set_var("_active", flag)
            return get_merged_context(context, vs_filterlist.from_html_vars(""))
    return context


class PageAjaxVisualFilterListGetChoice(ABCPageListOfMultipleGetChoice):
    def _get_choices(self, api_request):
        infos = api_request["infos"]
        return [
            ListOfMultipleChoiceGroup(
                title=visual_info_registry[info]().title, choices=VisualFilterList.get_choices(info)
            )
            for info in infos
        ]


def render_filter_form(
    info_list: SingleInfos, context: VisualContext, page_name: str, reset_ajax_page: str
) -> HTML:
    with output_funnel.plugged():
        show_filter_form(info_list, context, page_name, reset_ajax_page)
        return HTML(output_funnel.drain())


def show_filter_form(
    info_list: SingleInfos, context: VisualContext, page_name: str, reset_ajax_page: str
) -> None:
    html.show_user_errors()
    form_name: str = "filter"
    html.begin_form(
        form_name,
        method="GET",
        add_transid=False,
        onsubmit=f"cmk.forms.on_filter_form_submit_remove_vars({json.dumps('form_' + form_name)});",
    )
    varprefix = ""
    vs_filters = VisualFilterListWithAddPopup(info_list=info_list)

    filter_list_id = VisualFilterListWithAddPopup.filter_list_id(varprefix)
    filter_list_selected_id = filter_list_id + "_selected"
    _show_filter_form_buttons(
        varprefix, filter_list_id, vs_filters._page_request_vars, page_name, reset_ajax_page
    )

    html.open_div(id_=filter_list_selected_id, class_=["side_popup_content"])
    vs_filters.render_input(varprefix, context)
    html.close_div()

    forms.end()

    html.hidden_fields()
    html.end_form()
    html.javascript("cmk.utils.add_simplebar_scrollbar(%s);" % json.dumps(filter_list_selected_id))

    # The filter popup is shown automatically when it has been submitted before on page reload. To
    # know that the user closed the popup after filtering, we have to hook into the close_popup
    # function.
    html.final_javascript(
        "cmk.page_menu.register_on_open_handler('popup_filters', cmk.page_menu.on_filter_popup_open);"
        "cmk.page_menu.register_on_close_handler('popup_filters', cmk.page_menu.on_filter_popup_close);"
        f"cmk.forms.add_filter_form_error_listener('{filter_list_selected_id}');"
    )


def _show_filter_form_buttons(
    varprefix: str,
    filter_list_id: str,
    page_request_vars: Mapping[str, Any] | None,
    view_name: str,
    reset_ajax_page: str,
) -> None:
    html.open_div(class_="side_popup_controls")

    html.open_a(
        href="javascript:void(0);",
        onclick="cmk.page_menu.toggle_popup_filter_list(this, %s)" % json.dumps(filter_list_id),
        class_="add",
    )
    html.icon("add")
    html.div(_("Add filter"), class_="description")
    html.close_a()

    html.open_div(class_="update_buttons")
    html.button("%s_apply" % varprefix, _("Apply filters"), cssclass="apply hot")
    html.jsbutton(
        "%s_reset" % varprefix,
        _("Reset"),
        cssclass="reset",
        onclick="cmk.valuespecs.visual_filter_list_reset(%s, %s, %s, %s)"
        % (
            json.dumps(varprefix),
            json.dumps(page_request_vars),
            json.dumps(view_name),
            json.dumps(reset_ajax_page),
        ),
    )
    html.close_div()
    html.close_div()


# Realizes a Multisite/visual filter in a valuespec. It can render the filter form, get
# the filled in values and provide the filled in information for persistance.
class VisualFilter(ValueSpec[FilterHTTPVariables]):
    def __init__(  # pylint: disable=redefined-builtin
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


# Converts a context from the form { filtername : { ... } } into
# the for { infoname : { filtername : { } } for editing.
def pack_context_for_editing(context: VisualContext, info_keys: Sequence[InfoName]) -> dict:
    # We need to pack all variables into dicts with the name of the
    # info. Since we have no mapping from info the the filter variable,
    # we pack into every info every filter. The dict valuespec will
    # pick out what it needs. Yurks.
    return {info_name: context for info_name in info_keys}


def unpack_context_after_editing(packed_context: dict) -> VisualContext:
    return get_merged_context(*(its_context for _info_type, its_context in packed_context.items()))


# .
#   .--Misc----------------------------------------------------------------.
#   |                          __  __ _                                    |
#   |                         |  \/  (_)___  ___                           |
#   |                         | |\/| | / __|/ __|                          |
#   |                         | |  | | \__ \ (__                           |
#   |                         |_|  |_|_|___/\___|                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def is_single_site_info(info_key: InfoName) -> bool:
    return visual_info_registry[info_key]().single_site


def single_infos_spec(single_infos: SingleInfos) -> tuple[str, FixedValue]:
    return (
        "single_infos",
        FixedValue(
            value=single_infos,
            title=_("Show information of single"),
            totext=", ".join(single_infos)
            if single_infos
            else _("Not restricted to showing a specific object."),
        ),
    )


def get_missing_single_infos(single_infos: SingleInfos, context: VisualContext) -> set[FilterName]:
    return missing_context_filters(get_single_info_keys(single_infos), context)


def missing_context_filters(
    require_filters: set[FilterName], context: VisualContext
) -> set[FilterName]:
    set_filters = (
        filter_name
        for filter_name, filter_context in context.items()
        if any(filter_context.values())
    )

    return require_filters.difference(set_filters)


def visual_title(
    what: str,
    visual: Visual,
    context: VisualContext,
    skip_title_context: bool = False,
) -> str:
    title = _u(str(visual["title"]))

    # In case we have a site context given replace the $SITE$ macro in the titles.
    site_filter_vars = context.get("site", {})
    assert isinstance(site_filter_vars, dict)
    title = title.replace("$SITE$", site_filter_vars.get("site", ""))

    if visual["add_context_to_title"] and not skip_title_context:
        title = _add_context_title(context, visual["single_infos"], title)

    return title


def view_title(view_spec: ViewSpec, context: VisualContext) -> str:
    return visual_title("view", view_spec, context)


def _add_context_title(context: VisualContext, single_infos: Sequence[str], title: str) -> str:
    def filter_heading(
        filter_name: FilterName,
        filter_vars: FilterHTTPVariables,
    ) -> str | None:
        try:
            filt = get_filter(filter_name)
        except KeyError:
            return ""  # silently ignore not existing filters

        return filt.heading_info(filter_vars)

    extra_titles = [v for v in get_singlecontext_vars(context, single_infos).values() if v]

    # FIXME: Is this really only needed for visuals without single infos?
    if not single_infos:
        for filter_name, filt_vars in context.items():
            if heading := filter_heading(filter_name, filt_vars):
                extra_titles.append(heading)

    if extra_titles:
        title += " " + ", ".join(extra_titles)

    for fn in get_ubiquitary_filters():
        # Disable 'wato_folder' filter, if Setup is disabled or there is a single host view
        if fn == "wato_folder" and (not active_config.wato_enabled or "host" in single_infos):
            continue

        if heading := filter_heading(fn, context.get(fn, {})):
            title = heading + " - " + title

    return title


# Determines the names of HTML variables to be set in order to
# specify a specify row in a datasource with a certain info.
# Example: the info "history" (Event Console History) needs
# the variables "event_id" and "history_line" to be set in order
# to exactly specify one history entry.
@request_memoize()
def info_params(info_key: InfoName) -> list[FilterName]:
    return [key for key, _vs in visual_info_registry[info_key]().single_spec]


def get_single_info_keys(single_infos: SingleInfos) -> set[FilterName]:
    return set(chain.from_iterable(map(info_params, single_infos)))


def get_singlecontext_vars(context: VisualContext, single_infos: SingleInfos) -> dict[str, str]:
    # Link filters only happen when switching from (host/service)group
    # datasource to host/service datasource. As this function is datasource
    # unaware we optionally test for this posibility when (host/service)group
    # is a single info.
    link_filters = {
        "hostgroup": "opthostgroup",
        "servicegroup": "optservicegroup",
    }

    def var_value(filter_name: FilterName) -> str:
        if filter_vars := context.get(filter_name):
            if filt := filter_registry.get(filter_name):
                return filter_vars.get(filt.htmlvars[0], "")
        return ""

    return {
        key: var_value(key) or var_value(link_filters.get(key, ""))
        for key in get_single_info_keys(single_infos)
    }


@request_memoize()
def may_add_site_hint(
    visual_name: str,
    info_keys: SingleInfos,
    single_info_keys: SingleInfos,
    filter_names: tuple[FilterName, ...],
) -> bool:
    """Whether or not the site hint may be set when linking to a visual with the given details"""
    # When there is one non single site info used don't add the site hint
    if [info_key for info_key in single_info_keys if not is_single_site_info(info_key)]:
        return False

    # Alternatively when the infos allow a site hint it is also needed to skip the site hint based
    # on the filters used by the target visual
    for info_key in info_keys:
        for filter_key in visual_info_registry[info_key]().multiple_site_filters:
            if filter_key in filter_names:
                return False

    # Hack for servicedesc view which is meant to show all services with the given
    # description: Don't add the site filter for this view.
    if visual_name == "servicedesc":
        return False

    return True


# .
#   .--Popup Add-----------------------------------------------------------.
#   |          ____                              _       _     _           |
#   |         |  _ \ ___  _ __  _   _ _ __      / \   __| | __| |          |
#   |         | |_) / _ \| '_ \| | | | '_ \    / _ \ / _` |/ _` |          |
#   |         |  __/ (_) | |_) | |_| | |_) |  / ___ \ (_| | (_| |          |
#   |         |_|   \___/| .__/ \__,_| .__/  /_/   \_\__,_|\__,_|          |
#   |                    |_|         |_|                                   |
#   +----------------------------------------------------------------------+
#   |  Handling of adding a visual element to a dashboard, etc.            |
#   '----------------------------------------------------------------------'


def ajax_popup_add() -> None:
    # name is unused at the moment in this, hand over as empty name
    page_menu_dropdown = page_menu_dropdown_add_to_visual(
        add_type=request.get_ascii_input_mandatory("add_type"), name=""
    )[0]

    html.open_ul()

    for topic in page_menu_dropdown.topics:
        html.open_li()
        html.span(topic.title)
        html.close_li()

        for entry in topic.entries:
            html.open_li()

            if not isinstance(entry.item, PageMenuLink):
                html.write_text(f"Unhandled entry type '{type(entry.item)}': {entry.name}")
                continue

            html.open_a(
                href=entry.item.link.url,
                onclick=entry.item.link.onclick,
                target=entry.item.link.target,
            )
            html.icon(entry.icon_name or "trans")
            html.write_text(entry.title)
            html.close_a()
            html.close_li()

    html.close_ul()


def page_menu_dropdown_add_to_visual(add_type: str, name: str) -> list[PageMenuDropdown]:
    """Create the dropdown menu for adding a visual to other visuals / pagetypes

    Please not that this data structure is not only used for rendering the dropdown
    in the page menu. There is also the case of graphs which open a popup menu to
    show these entries.
    """

    visual_topics = []

    for visual_type_class in visual_type_registry.values():
        visual_type = visual_type_class()

        entries = list(visual_type.page_menu_add_to_entries(add_type))
        if not entries:
            continue

        visual_topics.append(
            PageMenuTopic(
                title=_("Add to %s") % visual_type.title,
                entries=entries,
            )
        )

    if add_type == "pnpgraph" and not cmk_version.is_raw_edition():
        visual_topics.append(
            PageMenuTopic(
                title=_("Export"),
                entries=[
                    PageMenuEntry(
                        title=_("Export as JSON"),
                        icon_name="download",
                        item=make_javascript_link("cmk.popup_menu.graph_export('graph_export')"),
                    ),
                    PageMenuEntry(
                        title=_("Export as PNG"),
                        icon_name="download",
                        item=make_javascript_link("cmk.popup_menu.graph_export('graph_image')"),
                    ),
                ],
            )
        )

    return [
        PageMenuDropdown(
            name="add_to",
            title=_("Add to"),
            topics=pagetypes.page_menu_add_to_topics(add_type) + visual_topics,
            popup_data=[
                add_type,
                _encode_page_context(g.get("page_context", {})),
                {
                    "name": name,
                },
            ],
        )
    ]


# TODO: VisualContext can't be part of the types, VisualContext has neither
# None nor str on the values. Thus unhelpfully set to Dict
def _encode_page_context(page_context: dict) -> dict:
    return {k: "" if v is None else v for k, v in page_context.items()}


def set_page_context(page_context: VisualContext) -> None:
    g.page_context = page_context


class CreateInfoModel(BaseModel):
    params: dict
    context: VisualContext | None


def ajax_add_visual() -> None:
    check_csrf_token()
    visual_type_name = request.get_str_input_mandatory("visual_type")  # dashboards / views / ...
    try:
        visual_type = visual_type_registry[visual_type_name]()
    except KeyError:
        raise MKUserError("visual_type", _("Invalid visual type"))

    visual_name = request.get_str_input_mandatory("visual_name")  # add to this visual

    # type of the visual to add (e.g. view)
    element_type = request.get_str_input_mandatory("type")

    create_info = request.get_model_mandatory(CreateInfoModel, "create_info")

    visual_type.add_visual_handler(
        visual_name,
        element_type,
        create_info.context,
        create_info.params,
    )
