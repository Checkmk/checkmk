#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
from enum import Enum
from itertools import chain, starmap
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from livestatus import LivestatusTestingError

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.type_defs import UserId

import cmk.gui.forms as forms
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.pagetypes as pagetypes
import cmk.gui.query_filters as query_filters
import cmk.gui.userdb as userdb
import cmk.gui.utils as utils
from cmk.gui import hooks
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKGeneralException, MKUserError
from cmk.gui.globals import config, g, html, output_funnel, request, transactions, user
from cmk.gui.i18n import _, _u
from cmk.gui.log import logger
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    make_javascript_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuTopic,
)
from cmk.gui.pages import page_registry
from cmk.gui.permissions import declare_permission, permission_registry

# Needed for legacy (pre 1.6) plugins
from cmk.gui.plugins.visuals.utils import (  # noqa: F401 # pylint: disable=unused-import
    active_filter_flag,
    collect_filters,
    Filter,
    filter_registry,
    FilterOption,
    filters_allowed_for_info,
    filters_allowed_for_infos,
    FilterTime,
    get_livestatus_filter_headers,
    get_only_sites_from_context,
    visual_info_registry,
    visual_type_registry,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import (
    FilterHTTPVariables,
    FilterName,
    HTTPVariables,
    InfoName,
    SingleInfos,
    Visual,
    VisualContext,
    VisualName,
    VisualTypeName,
)
from cmk.gui.utils import unique_default_name_suggestion, validate_id
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.html import HTML
from cmk.gui.utils.logged_in import save_user_file
from cmk.gui.utils.roles import is_user_with_publish_permissions, user_may
from cmk.gui.utils.urls import (
    file_name_and_query_vars_from_url,
    make_confirm_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
    urlencode,
)
from cmk.gui.valuespec import (
    ABCPageListOfMultipleGetChoice,
    CascadingDropdown,
    Checkbox,
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
    ValueSpecText,
)

CustomUserVisuals = Dict[Tuple[UserId, VisualName], Dict]


class VisualType(Enum):
    views: VisualTypeName = "views"
    dashboards: VisualTypeName = "dashboards"
    reports: VisualTypeName = "reports"


T = TypeVar("T")
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

title_functions: List[Callable] = []


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    global title_functions
    title_functions = []
    _register_pre_21_plugin_api()
    utils.load_web_plugins("visuals", globals())


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.
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


# TODO: This has been obsoleted by pagetypes.py
def declare_visual_permissions(what, what_plural):
    declare_permission(
        "general.edit_" + what,
        _("Customize %s and use them") % what_plural,
        _("Allows to create own %s, customize builtin %s and use them.")
        % (what_plural, what_plural),
        ["admin", "user"],
    )

    declare_permission(
        "general.publish_" + what,
        _("Publish %s") % what_plural,
        _("Make %s visible and usable for all users.") % what_plural,
        ["admin", "user"],
    )

    declare_permission(
        "general.publish_" + what + "_to_groups",
        _("Publish %s to allowed contact groups") % what_plural,
        _(
            "Make %s visible and usable for users of contact groups the publishing user is a member of."
        )
        % what_plural,
        ["admin", "user"],
    )

    declare_permission(
        "general.publish_" + what + "_to_foreign_groups",
        _("Publish %s to foreign contact groups") % what_plural,
        _(
            "Make %s visible and usable for users of contact groups the publishing user is not a member of."
        )
        % what_plural,
        ["admin"],
    )

    declare_permission(
        "general.see_user_" + what,
        _("See user %s") % what_plural,
        _("Is needed for seeing %s that other users have created.") % what_plural,
        ["admin", "user", "guest"],
    )

    declare_permission(
        "general.force_" + what,
        _("Modify builtin %s") % what_plural,
        _("Make own published %s override builtin %s for all users.") % (what_plural, what_plural),
        ["admin"],
    )

    declare_permission(
        "general.edit_foreign_" + what,
        _("Edit foreign %s") % what_plural,
        _("Allows to edit %s created by other users.") % what_plural,
        ["admin"],
    )

    declare_permission(
        "general.delete_foreign_" + what,
        _("Delete foreign %s") % what_plural,
        _("Allows to delete %s created by other users.") % what_plural,
        ["admin"],
    )


# .
#   .--Save/Load-----------------------------------------------------------.
#   |          ____                     ___                    _           |
#   |         / ___|  __ ___   _____   / / |    ___   __ _  __| |          |
#   |         \___ \ / _` \ \ / / _ \ / /| |   / _ \ / _` |/ _` |          |
#   |          ___) | (_| |\ V /  __// / | |__| (_) | (_| | (_| |          |
#   |         |____/ \__,_| \_/ \___/_/  |_____\___/ \__,_|\__,_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def save(what, visuals, user_id=None):
    if user_id is None:
        user_id = user.id
    assert user_id is not None

    uservisuals = {}
    for (owner_id, name), visual in visuals.items():
        if user_id == owner_id:
            uservisuals[name] = visual
    save_user_file("user_" + what, uservisuals, user_id=user_id)
    _CombinedVisualsCache(VisualType(what)).invalidate_cache()


def load(
    what: str,
    builtin_visuals: Dict[Any, Any],
    skip_func: Optional[Callable[[Dict[Any, Any]], bool]] = None,
) -> Dict[Tuple[UserId, str], Dict[str, Any]]:
    visuals: Dict[Tuple[UserId, str], Dict[str, Any]] = {}

    # first load builtins. Set username to ''
    for name, visual in builtin_visuals.items():
        visual["owner"] = ""  # might have been forgotten on copy action
        visual["public"] = True
        visual["name"] = name

        # Dashboards had not all COMMON fields in previous versions. Add them
        # here to be compatible for a specific time. Seamless migration, yeah.
        visual.setdefault("description", "")
        visual.setdefault("hidden", False)

        visuals[(UserId(""), name)] = visual

    # Add custom "user_*.mk" visuals
    visuals.update(_CombinedVisualsCache(VisualType(what)).load(builtin_visuals, skip_func))

    return visuals


# This is currently not called by load() because some visual type (e.g. view) specific transform
# needs to be executed in advance. This should be cleaned up.
def transform_old_visual(visual):
    """Prepare visuals for working with them. Migrate old formats or add default settings, for example"""
    visual.setdefault("single_infos", [])
    visual.setdefault("context", {})
    visual.setdefault("link_from", {})
    visual.setdefault("topic", "")
    visual.setdefault("icon", None)

    # 1.6 introduced this setting: Ensure all visuals have it set
    visual.setdefault("add_context_to_title", True)

    # 1.7 introduced these settings for the new mega menus
    visual.setdefault("sort_index", 99)
    visual.setdefault("is_show_more", False)

    # 2.1
    visual["context"] = cleanup_context_filters(visual["context"], visual["single_infos"])


def transform_pre_2_1_discovery_state(
    fident: FilterName, vals: FilterHTTPVariables
) -> Tuple[FilterName, FilterHTTPVariables]:
    # Fix context into type VisualContext
    if fident == "discovery_state":
        return "discovery_state", {key: "on" if val else "" for key, val in vals.items()}
    return fident, vals


def transform_pre_2_1_single_infos(
    single_infos: SingleInfos,
) -> Callable[
    [FilterName, Union[str, int, FilterHTTPVariables]], Tuple[FilterName, FilterHTTPVariables]
]:
    # Remove the old single infos
    single_info_keys = get_single_info_keys(single_infos)

    def unsingle(
        fident: FilterName, vals: Union[str, int, FilterHTTPVariables]
    ) -> Tuple[FilterName, FilterHTTPVariables]:
        if isinstance(vals, dict):  # Alredy FilterHTTPVariables
            return fident, vals
        # Single infos come from VisualInfo children. They have a str or int valuespec
        if fident in single_info_keys:
            filt = get_filter(fident)
            return filt.ident, {filt.htmlvars[0]: str(vals)}
        if fident in ["site", "sites", "siteopt"]:  # Because the site hint is not a VisualInfo
            htmlvar = "site" if fident == "siteopt" else fident
            return fident, {htmlvar: str(vals)}

        # should never happen
        raise MKGeneralException(
            "Unexpected configuration of context variable: Filter '%s' with value %r"
            % (fident, vals)
        )

    return unsingle


def transform_pre_2_1_range_filters() -> Callable[
    [FilterName, FilterHTTPVariables], Tuple[FilterName, FilterHTTPVariables]
]:
    # Update Visual Range Filters
    range_filters = [
        filter_ident
        for filter_ident, filter_object in filter_registry.items()
        if hasattr(filter_object, "query_filter")
        and isinstance(filter_object.query_filter, query_filters.NumberRangeQuery)  # type: ignore[attr-defined]
    ]

    def transform_range_vars(
        fident: FilterName, vals: FilterHTTPVariables
    ) -> Tuple[FilterName, FilterHTTPVariables]:
        if fident in range_filters:
            return fident, {
                re.sub("_to(_|$)", "_until\\1", request_var): value
                for request_var, value in vals.items()
            }
        return fident, vals

    return transform_range_vars


def cleanup_context_filters(context, single_infos: SingleInfos) -> VisualContext:
    new_context_vars = starmap(transform_pre_2_1_single_infos(single_infos), context.items())
    new_context_vars = starmap(transform_pre_2_1_discovery_state, new_context_vars)
    new_context_vars = starmap(transform_pre_2_1_range_filters(), new_context_vars)

    return dict(new_context_vars)


class _CombinedVisualsCache:
    _visuals_cache_dir: Final[Path] = Path(cmk.utils.paths.tmp_dir) / "visuals_cache"

    def __init__(self, visual_type: VisualType):
        self._visual_type: Final[VisualType] = visual_type

    @classmethod
    def invalidate_all_caches(cls) -> None:
        for visual_type in VisualType:
            _CombinedVisualsCache(visual_type).invalidate_cache()

    def invalidate_cache(self) -> None:
        self._update_cache_info_timestamp()

    def _update_cache_info_timestamp(self) -> None:
        cache_info_filename = self._info_filename
        cache_info_filename.parent.mkdir(parents=True, exist_ok=True)
        cache_info_filename.touch()

    @property
    def _info_filename(self) -> Path:
        return self._visuals_cache_dir / f"last_update_{self._visual_type.value}"

    @property
    def _content_filename(self) -> Path:
        return self._visuals_cache_dir / f"cached_{self._visual_type.value}"

    def load(
        self,
        builtin_visuals: Dict[Any, Any],
        skip_func: Optional[Callable[[Dict[Any, Any]], bool]],
    ) -> CustomUserVisuals:

        if self._may_use_cache():
            if (content := self._read_from_cache()) is not None:
                return content
        return self._compute_and_write_cache(builtin_visuals, skip_func)

    def _may_use_cache(self) -> bool:
        if not self._content_filename.exists():
            return False

        if not self._info_filename.exists():
            # Create a new file for future reference (this obviously has the newest timestamp)
            self.invalidate_cache()
            return False

        if self._content_filename.stat().st_mtime < self._info_filename.stat().st_mtime:
            return False

        return True

    def _compute_and_write_cache(
        self,
        builtin_visuals: Dict[Any, Any],
        skip_func: Optional[Callable[[Dict[Any, Any]], bool]],
    ) -> CustomUserVisuals:
        visuals = _load_custom_user_visuals(self._visual_type.value, builtin_visuals, skip_func)
        self._write_to_cache(visuals)
        return visuals

    def _read_from_cache(self) -> Optional[CustomUserVisuals]:
        try:
            return pickle.loads(store.load_bytes_from_file(self._content_filename))
        except (TypeError, pickle.UnpicklingError):
            return None

    def _write_to_cache(self, visuals: CustomUserVisuals) -> None:
        store.save_bytes_to_file(self._content_filename, pickle.dumps(visuals))
        self._update_cache_info_timestamp()


hooks.register_builtin("snapshot-pushed", _CombinedVisualsCache.invalidate_all_caches)
hooks.register_builtin("users-saved", lambda x: _CombinedVisualsCache.invalidate_all_caches())


def _load_custom_user_visuals(
    what: str,
    builtin_visuals: Dict[Any, Any],
    skip_func: Optional[Callable[[Dict[Any, Any]], bool]],
) -> CustomUserVisuals:
    """Note: Try NOT to use pathlib.Path functionality in this function, as pathlib is
    measurably slower (7 times), due to path object creation and concatenation. This function
    can iterate over several thousand files, which may take 250ms (Path) or 50ms(os.path)"""

    visuals: CustomUserVisuals = {}
    visual_filename = "user_%s.mk" % what
    old_views_filename = "views.mk"

    for dirname in cmk.utils.paths.profile_dir.iterdir():
        try:
            user_dirname = os.path.join(cmk.utils.paths.profile_dir, dirname)
            visual_path = os.path.join(user_dirname, visual_filename)
            # Be compatible to old views.mk. The views.mk contains customized views
            # in an old format which will be loaded, transformed and when saved stored
            # in users_views.mk. When this file exists only this file is used.
            if what == "views" and not os.path.exists(visual_path):
                visual_path = os.path.join(user_dirname, old_views_filename)

            if not os.path.exists(visual_path):
                continue

            user_id = os.path.basename(dirname)
            if not userdb.user_exists(UserId(user_id)):
                continue

            visuals.update(
                load_visuals_of_a_user(what, builtin_visuals, skip_func, visual_path, user_id)
            )

        except SyntaxError as e:
            raise MKGeneralException(_("Cannot load %s from %s: %s") % (what, visual_path, e))

    return visuals


def load_visuals_of_a_user(what, builtin_visuals, skip_func, path, user_id) -> CustomUserVisuals:
    user_visuals: CustomUserVisuals = {}
    for name, visual in store.load_object_from_file(path, default={}).items():
        visual["owner"] = user_id
        visual["name"] = name

        if skip_func and skip_func(visual):
            continue

        # Maybe resolve inherited attributes. This was a feature for several versions
        # to make the visual texts localizable. This has been removed because the visual
        # texts can now be localized using the custom localization strings.
        # This is needed for backward compatibility to make the visuals without these
        # attributes get the attributes from their builtin visual.
        builtin_visual = builtin_visuals.get(name)
        if builtin_visual:
            for attr in ["title", "topic", "description"]:
                if attr not in visual and attr in builtin_visual:
                    visual[attr] = builtin_visual[attr]

        # Repair visuals with missing 'title' or 'description'
        visual.setdefault("title", name)
        visual.setdefault("description", "")

        # Declare custom permissions
        declare_visual_permission(what, name, visual)

        user_visuals[(user_id, name)] = visual

    return user_visuals


def declare_visual_permission(what, name, visual):
    permname = "%s.%s" % (what[:-1], name)
    if visual["public"] and permname not in permission_registry:
        declare_permission(
            permname, visual["title"], visual["description"], ["admin", "user", "guest"]
        )


# Load all users visuals just in order to declare permissions of custom visuals
def declare_custom_permissions(what):
    for dirpath in cmk.utils.paths.profile_dir.iterdir():
        try:
            if dirpath.is_dir():
                path = dirpath.joinpath("%s.mk" % what)
                if not path.exists():
                    continue
                visuals = store.load_object_from_file(path, default={})
                for name, visual in visuals.items():
                    declare_visual_permission(what, name, visual)
        except Exception:
            if config.debug:
                raise


# Get the list of visuals which are available to the user
# (which could be retrieved with get_visual)
def available(
    what: str, all_visuals: Dict[Tuple[UserId, VisualName], Visual]
) -> Dict[VisualName, Visual]:
    visuals = {}
    permprefix = what[:-1]

    def published_to_user(visual: Visual) -> bool:
        if visual["public"] is True:
            return True

        if isinstance(visual["public"], tuple) and visual["public"][0] == "contact_groups":
            user_groups = set([] if user.id is None else userdb.contactgroups_of_user(user.id))
            return bool(user_groups.intersection(visual["public"][1]))
        return False

    def restricted_visual(visualname: VisualName):
        permname = "%s.%s" % (permprefix, visualname)
        return permname in permission_registry and not user.may(permname)

    # 1. user's own visuals, if allowed to edit visuals
    if user.may("general.edit_" + what):
        for (u, n), visual in all_visuals.items():
            if u == user.id:
                visuals[n] = visual

    # 2. visuals of special users allowed to globally override builtin visuals
    for (u, n), visual in all_visuals.items():
        # Honor original permissions for the current user
        if (
            n not in visuals
            and published_to_user(visual)
            and user_may(u, "general.force_" + what)
            and not restricted_visual(n)
        ):
            visuals[n] = visual

    # 3. Builtin visuals, if allowed.
    for (u, n), visual in all_visuals.items():
        if u == "" and n not in visuals and user.may("%s.%s" % (permprefix, n)):
            visuals[n] = visual

    # 4. other users visuals, if public. Still make sure we honor permission
    #    for builtin visuals. Also the permission "general.see_user_visuals" is
    #    necessary.
    if user.may("general.see_user_" + what):
        for (u, n), visual in all_visuals.items():
            # Is there a builtin visual with the same name? If yes, honor permissions.
            if (
                n not in visuals
                and published_to_user(visual)
                and user_may(u, "general.publish_" + what)
                and not restricted_visual(n)
            ):
                visuals[n] = visual

    return visuals


def get_permissioned_visual(
    item: str,
    owner: Optional[str],
    what: str,
    permitted_visuals: Dict[str, T],
    all_visuals: Dict[Tuple[UserId, str], T],
) -> T:
    if (
        owner is not None
        and owner != user.id  # Var is set from edit page and can be empty string for builtin
        and user.may(  # user has top priority, thus only change if other user
            "general.edit_foreign_%ss" % what
        )
    ):
        if visual := all_visuals.get((UserId(owner), item)):
            return visual
        # We don't raise on not found immediately and let it trickle down to default permitted
        # as a failsafe for report inheritance. In general it is OK for other cases, because the
        # priority should be inverse, first pick from permitted, then if edit_foreign permissions
        # are available get from other user. In reports it still happens that the inheritance view
        # is of the active user not of the "owner". Resolution of those piorities would need to be
        # fixed in visuals.available to support foreign users.

    if visual := permitted_visuals.get(item):
        return visual

    raise MKUserError("%s_name" % what, _("The requested %s %s does not exist") % (what, item))


# .
#   .--Listing-------------------------------------------------------------.
#   |                    _     _     _   _                                 |
#   |                   | |   (_)___| |_(_)_ __   __ _                     |
#   |                   | |   | / __| __| | '_ \ / _` |                    |
#   |                   | |___| \__ \ |_| | | | | (_| |                    |
#   |                   |_____|_|___/\__|_|_| |_|\__, |                    |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+
#   | Show a list of all visuals with actions to delete/clone/edit         |
#   '----------------------------------------------------------------------'


# TODO: This code has been copied to a new live into htdocs/pagetypes.py
# We need to convert all existing page types (views, dashboards, reports)
# to pagetypes.py and then remove this function!
def page_list(
    what,
    title,
    visuals,
    custom_columns=None,
    render_custom_buttons=None,
    render_custom_columns=None,
    custom_page_menu_entries=None,
    check_deletable_handler=None,
):

    if custom_columns is None:
        custom_columns = []

    what_s = what[:-1]
    if not user.may("general.edit_" + what):
        raise MKAuthException(_("Sorry, you lack the permission for editing this type of visuals."))

    breadcrumb = visual_page_breadcrumb(what, title, "list")

    visual_type = visual_type_registry[what]()
    visual_plural_title = visual_type.plural_title.title()
    current_type_dropdown = PageMenuDropdown(
        name=what,
        title=visual_plural_title,
        topics=[
            PageMenuTopic(
                title=visual_plural_title,
                entries=[
                    PageMenuEntry(
                        title=_("Add %s") % visual_type.title,
                        icon_name="new",
                        item=make_simple_link("create_%s.py" % what_s),
                        is_shortcut=True,
                        is_suggested=True,
                    ),
                ]
                + (list(custom_page_menu_entries()) if custom_page_menu_entries else []),
            ),
        ],
    )

    page_menu = pagetypes.customize_page_menu(
        breadcrumb,
        current_type_dropdown,
        what,
    )
    html.header(title, breadcrumb, page_menu)

    for message in get_flashed_messages():
        html.show_message(message)

    # Deletion of visuals
    delname = request.var("_delete")
    if delname and transactions.check_transaction():
        if user.may("general.delete_foreign_%s" % what):
            user_id_str = request.get_str_input("_user_id", user.id)
            user_id = None if user_id_str is None else UserId(user_id_str)
        else:
            user_id = user.id

        try:
            if check_deletable_handler:
                check_deletable_handler(visuals, user_id, delname)

            del visuals[(user_id, delname)]
            save(what, visuals, user_id)
            flash(_("Your %s has been deleted.") % visual_type.title)
            html.reload_whole_page()
        except MKUserError as e:
            html.user_error(e)

    available_visuals = available(what, visuals)
    for title1, visual_group in _partition_visuals(visuals, what):
        html.h3(title1, class_="table")

        with table_element(css="data", limit=None) as table:

            for owner, visual_name, visual in visual_group:
                table.row(css="data")

                # Actions
                table.cell(_("Actions"), css="buttons visuals")

                # Clone / Customize
                buttontext = _("Create a customized copy of this")
                backurl = urlencode(makeuri(request, []))
                clone_url = makeuri_contextless(
                    request,
                    [
                        ("mode", "clone"),
                        ("owner", owner),
                        ("load_name", visual_name),
                        ("back", backurl),
                    ],
                    filename="edit_%s.py" % what_s,
                )
                html.icon_button(clone_url, buttontext, "clone")

                # Delete
                if owner and (owner == user.id or user.may("general.delete_foreign_%s" % what)):
                    add_vars: HTTPVariables = [("_delete", visual_name)]
                    if owner != user.id:
                        add_vars.append(("_user_id", owner))
                    html.icon_button(
                        make_confirm_link(
                            url=makeactionuri(request, transactions, add_vars),
                            message=_('Please confirm the deletion of "%s".') % visual["title"],
                        ),
                        _("Delete!"),
                        "delete",
                    )

                # Edit
                if owner == user.id or (owner != "" and user.may("general.edit_foreign_%s" % what)):
                    edit_vars: HTTPVariables = [
                        ("mode", "edit"),
                        ("load_name", visual_name),
                    ]
                    if owner != user.id:
                        edit_vars.append(("owner", owner))
                    edit_url = makeuri_contextless(
                        request,
                        edit_vars,
                        filename="edit_%s.py" % what_s,
                    )
                    html.icon_button(edit_url, _("Edit"), "edit")

                # Custom buttons - visual specific
                if render_custom_buttons:
                    render_custom_buttons(visual_name, visual)

                # visual Name
                table.cell(_("ID"), visual_name)

                # Title
                table.cell(_("Title"))
                title2 = _u(visual["title"])
                if _visual_can_be_linked(what, visual_name, available_visuals, visual, owner):
                    show_url = makeuri_contextless(
                        request,
                        [(visual_type_registry[what]().ident_attr, visual_name), ("owner", owner)],
                        filename="%s.py" % what_s,
                    )
                    html.a(title2, href=show_url)
                else:
                    html.write_text(title2)
                html.help(_u(visual["description"]))

                # Custom cols
                for title3, renderer in custom_columns:
                    table.cell(title3, renderer(visual))

                # Owner
                if owner == "":
                    ownertxt = "<i>" + _("builtin") + "</i>"
                else:
                    ownertxt = owner
                table.cell(_("Owner"), ownertxt)
                table.cell(_("Public"), visual["public"] and _("yes") or _("no"))
                table.cell(_("Hidden"), visual["hidden"] and _("yes") or _("no"))

                if render_custom_columns:
                    render_custom_columns(table, visual_name, visual)

    html.footer()


def _visual_can_be_linked(what, visual_name, user_visuals, visual, owner):
    if owner == user.id or user.may("general.edit_foreign_%s" % what):
        return True

    # Is this the highest priority visual that the user has available?
    if user_visuals.get(visual_name) != visual:
        return False

    return visual["public"]


def _partition_visuals(
    visuals: Dict[Tuple[UserId, str], Dict], what: str
) -> List[Tuple[str, List[Tuple[UserId, str, Dict]]]]:
    keys_sorted = sorted(visuals.keys(), key=lambda x: (x[1], x[0]))

    my_visuals, foreign_visuals, builtin_visuals = [], [], []
    for (owner, visual_name) in keys_sorted:
        if owner == "" and not user.may("%s.%s" % (what[:-1], visual_name)):
            continue  # not allowed to see this view

        visual = visuals[(owner, visual_name)]
        if visual["public"] and owner == "":
            builtin_visuals.append((owner, visual_name, visual))
        elif owner == user.id:
            my_visuals.append((owner, visual_name, visual))
        elif (
            visual["public"] and owner != "" and user_may(owner, "general.publish_%s" % what)
        ) or user.may("general.edit_foreign_%s" % what):
            foreign_visuals.append((owner, visual_name, visual))

    return [
        (_("Customized"), my_visuals),
        (_("Owned by other users"), foreign_visuals),
        (_("Builtin"), builtin_visuals),
    ]


# .
#   .--Create Visual-------------------------------------------------------.
#   |      ____                _        __     ___                 _       |
#   |     / ___|_ __ ___  __ _| |_ ___  \ \   / (_)___ _   _  __ _| |      |
#   |    | |   | '__/ _ \/ _` | __/ _ \  \ \ / /| / __| | | |/ _` | |      |
#   |    | |___| | |  __/ (_| | ||  __/   \ V / | \__ \ |_| | (_| | |      |
#   |     \____|_|  \___|\__,_|\__\___|    \_/  |_|___/\__,_|\__,_|_|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Realizes the steps before getting to the editor (context type)       |
#   '----------------------------------------------------------------------'


def page_create_visual(what, info_keys, next_url=None):
    visual_name = visual_type_registry[what]().title
    title = _("Create %s") % visual_name
    what_s = what[:-1]

    vs_infos = SingleInfoSelection(info_keys)

    breadcrumb = visual_page_breadcrumb(what, title, "create")
    html.header(
        title,
        breadcrumb,
        make_simple_form_page_menu(
            visual_name.capitalize(),
            breadcrumb,
            form_name="create_visual",
            button_name="_save",
            save_title=_("Continue"),
        ),
    )

    html.open_p()
    html.write_text(
        _(
            "Depending on the chosen datasource, a %s can list <i>multiple</i> or <i>single</i> objects. "
            "For example, the <i>services</i> datasource can be used to simply create a list "
            "of <i>multiple</i> services, a list of <i>multiple</i> services of a <i>single</i> host or even "
            "a list of services with the same name on <i>multiple</i> hosts. When you just want to "
            "create a list of objects, simply continue with the default choice (no restrictions). "
            "Alternatively, you have the option to restrict to a single host or to choose the type "
            "of objects you want to restrict to manually."
        )
        % what_s
    )
    html.close_p()

    if request.var("_save") and transactions.check_transaction():
        try:
            single_infos = vs_infos.from_html_vars("single_infos")
            vs_infos.validate_value(single_infos, "single_infos")
            next_url = (
                next_url or "edit_" + what_s + ".py?mode=create"
            ) + "&single_infos=%s" % ",".join(single_infos)
            raise HTTPRedirect(next_url)
        except MKUserError as e:
            html.user_error(e)

    html.begin_form("create_visual")
    html.hidden_field("mode", "create")

    forms.header(_("Select specific object type"))
    forms.section(vs_infos.title())
    vs_infos.render_input("single_infos", "")
    html.help(vs_infos.help())
    forms.end()

    html.hidden_fields()
    html.end_form()
    html.footer()


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


def get_context_specs(visual, info_handler):
    info_keys = list(visual_info_registry.keys())
    if info_handler:
        handler_keys = info_handler(visual)
        if handler_keys is not None:
            info_keys = handler_keys

    single_info_keys = [key for key in info_keys if key in visual["single_infos"]]
    multi_info_keys = [key for key in info_keys if key not in single_info_keys]

    def host_service_lead(val):
        # Sort is stable in python, thus only prioritize host>service>rest
        if val[0] == "host":
            return 0
        if val[0] == "service":
            return 1
        return 2

    # single infos first, the rest afterwards
    context_specs = [(info_key, visual_spec_single(info_key)) for info_key in single_info_keys] + [
        (info_key, visual_spec_multi(info_key))
        for info_key in multi_info_keys
        if visual_spec_multi(info_key)
    ]

    return sorted(context_specs, key=host_service_lead)


def visual_spec_single(info_key):
    # VisualInfos have a single_spec, which might declare multiple filters.
    # In this case each spec is as filter value and it is typed(at the moment only Integer & TextInput).
    # Filters at the moment, due to use of url_vars, are string only.
    # At the moment single_info_spec relation to filters is:
    #     for all (i): info.single_spec[i][0]==filter.ident==filter.htmlvars[0]

    # This visual_spec_single stores direct into the VisualContext, thus it needs to dissosiate
    # the single_spec into separate filters. This transformations are the equivalent of flattening
    # the values into the url, but now they preserve the VisualContext type.

    # In both cases unused keys need to be removed otherwise empty values proliferate
    # either they are saved or they corrupt the VisualContext during merges.

    def back(
        values: Dict[str, Union[str, int]], single_spec: List[Tuple[FilterName, ValueSpec]]
    ) -> VisualContext:
        return {
            ident: {ident: str(value)}
            for ident, _vs in single_spec
            for value in [values.get(ident)]
            if value
        }

    def forth(
        context: VisualContext, single_spec: List[Tuple[FilterName, ValueSpec]]
    ) -> Dict[str, Union[str, int]]:
        return {
            ident: value
            for ident, vs in single_spec
            for value in [context.get(ident, {}).get(ident)]
            if value
        }

    info = visual_info_registry[info_key]()

    return Transform(
        Dictionary(
            title=info.title,
            form_isopen=True,
            optional_keys=True,
            elements=info.single_spec,
        ),
        back=lambda values: back(values, info.single_spec),
        forth=lambda context: forth(context, info.single_spec),
    )


def visual_spec_multi(info_key):
    info = visual_info_registry[info_key]()
    filter_list = VisualFilterList([info_key], title=info.title)
    filter_names = filter_list.filter_names()
    # Skip infos which have no filters available
    return filter_list if filter_names else None


def process_context_specs(context_specs) -> VisualContext:
    context = {}
    for info_key, spec in context_specs:
        ident = "context_" + info_key

        attrs = spec.from_html_vars(ident)
        spec.validate_value(attrs, ident)
        context.update(attrs)
    return context


def render_context_specs(
    visual,
    context_specs,
    isopen: bool = True,
    help_text: Union[str, HTML, None] = None,
):
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
    value = visual.get("context", {})
    for info_key, spec in context_specs:
        forms.section(
            spec.title(),
            is_show_more=spec.has_show_more()
            if isinstance(spec, Transform)
            else all(flt.is_show_more for _title, flt in spec.filter_items() if flt is not None),
        )
        ident = "context_" + info_key
        spec.render_input(ident, value)


def _vs_general(
    single_infos,
    default_id,
    visual_type,
    visibility_elements,
    all_visuals: Dict[Tuple[UserId, VisualName], Visual],
    mode: str,
    what: str,
):
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
                        "topic name you can do this here <a href='%s'>here</a>."
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


def page_edit_visual(
    what: Literal["dashboards", "views", "reports"],
    all_visuals: Dict[Tuple[UserId, VisualName], Visual],
    custom_field_handler=None,
    create_handler=None,
    load_handler=None,
    info_handler=None,
    sub_pages: Optional[pagetypes.SubPagesSpec] = None,
    help_text_context: Union[str, HTML, None] = None,
):
    if sub_pages is None:
        sub_pages = []

    visual_type = visual_type_registry[what]()
    if not user.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % visual_type.plural_title)
    visual: Dict[str, Any] = {
        "link_from": {},
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

    if visualname:
        owner_id = UserId(request.get_str_input_mandatory("owner", user.id))
        visual = _get_visual(owner_id, mode)

        if mode == "edit" and owner_id != "":  # editing builtins requires copy
            owner_user_id = owner_id
            title = _("Edit %s") % visual_type.title
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

        if load_handler:
            load_handler(visual)

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

    back_url = request.get_url_input("back", "edit_%s.py" % what)

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
    html.header(title, breadcrumb, page_menu)

    # A few checkboxes concerning the visibility of the visual. These will
    # appear as boolean-keys directly in the visual dict, but encapsulated
    # in a list choice in the value spec.
    visibility_elements: List[Tuple[str, ValueSpec]] = [
        (
            "hidden",
            FixedValue(
                True,
                title=_("Hide this %s in the monitor menu") % visual_type.title,
                totext="",
            ),
        ),
        (
            "hidebutton",
            FixedValue(
                True,
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
    context_specs = get_context_specs(visual, info_handler)

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

            if not user.may("general.publish_" + what):
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
                    back_url_from_vars = html.request.var("back")
                    if back_url_from_vars:
                        _file_name, query_vars = file_name_and_query_vars_from_url(
                            back_url_from_vars
                        )
                        back_vars = [(varname, value[0]) for varname, value in query_vars.items()]
                    visual_name_var: Tuple[str, str] = (visual_type.ident_attr, visual["name"])
                    if visual_name_var not in back_vars:
                        back_vars.append(visual_name_var)

                    back_url = makeuri_contextless(
                        request,
                        back_vars,
                        filename=visual_type.show_url,
                    )

                if transactions.check_transaction():
                    assert owner_user_id is not None
                    all_visuals[(owner_user_id, visual["name"])] = visual
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

    vs_general.render_input("general", visual)

    if custom_field_handler and custom_field_handler.__name__ != "dashboard_fields_handler":
        custom_field_handler(visual)

    render_context_specs(
        visual,
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
        html.icon("alert", _("This filter cannot be displayed") + " (%s)\n%s" % (e, "".join(tbs)))
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
    info_keys: List[InfoName],
    link_filters: Dict[FilterName, FilterName],
) -> Iterator[Tuple[FilterName, FilterName]]:
    for info_key in single_infos:
        if info_key not in info_keys:
            for key in info_params(info_key):
                if key in link_filters:
                    yield key, link_filters[key]


def filters_of_visual(
    visual: Visual,
    info_keys: List[InfoName],
    link_filters: Optional[Dict[FilterName, FilterName]] = None,
) -> List[Filter]:
    """Collects all filters to be used for the given visual"""
    if link_filters is None:
        link_filters = {}

    filters: Dict[FilterName, Filter] = {}

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
        # Disable 'wato_folder' filter, if WATO is disabled or there is a single host view
        filter_ = get_filter(fn)

        if fn == "wato_folder" and (not filter_.available() or "host" in visual["single_infos"]):
            continue
        if not filter_.info or filter_.info in info_keys:
            filters[fn] = filter_

    return list(filters.values())


# TODO: Cleanup this special case
def get_ubiquitary_filters() -> List[FilterName]:
    return ["wato_folder"]


# Reduces the list of the visuals used filters. The result are the ones
# which are really presented to the user later.
# For the moment we only remove the single context filters which have a
# hard coded default value which is treated as enforced value.
def visible_filters_of_visual(visual: Visual, use_filters: List[Filter]) -> List[Filter]:
    show_filters = []

    single_keys = get_single_info_keys(visual["single_infos"])

    for f in use_filters:
        if f.ident not in single_keys or not visual["context"].get(f.ident):
            show_filters.append(f)

    return show_filters


def context_to_uri_vars(context: VisualContext) -> HTTPVariables:
    """Produce key/value tuples for HTTP variables from the visual context"""
    # return list(chain.from_iterable(filter_vars.items() for filter_vars in context.values()))
    # During CMK 2.1 beta look for things to break. If no bugs are found use line above
    uri_vars: HTTPVariables = []
    for filter_vars in context.values():
        for uri_varname, value in filter_vars.items():
            assert isinstance(value, str)
            uri_vars.append((uri_varname, value))
    return uri_vars


# Vice versa: find all filters that belong to the current URI variables
# and create a context dictionary from that.
def get_context_from_uri_vars(only_infos: Optional[List[InfoName]] = None) -> VisualContext:
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
def get_filter_headers(table, infos, context: VisualContext):
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


def FilterChoices(
    infos: List[InfoName], title: str, help: str
):  # pylint: disable=redefined-builtin
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
    def get_choices(cls, info: str) -> Sequence[Tuple[str, VisualFilter]]:
        return sorted(
            cls._get_filter_specs(info), key=lambda x: (x[1]._filter.sort_index, x[1].title())
        )

    @classmethod
    def _get_filter_specs(cls, info: str) -> Iterator[Tuple[str, VisualFilter]]:
        for fname, filter_ in filters_allowed_for_info(info):
            yield fname, VisualFilter(fname, title=filter_.title)

    def __init__(self, info_list, **kwargs):
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
            grouped,
            "ajax_visual_filter_list_get_choice",
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
                    id_="%s_add_%s" % (varprefix, filter_name),
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


def active_context_from_request(infos: List[str], context: VisualContext) -> VisualContext:
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


@page_registry.register_page("ajax_visual_filter_list_get_choice")
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
    info_list: List[InfoName], context: VisualContext, page_name: str, reset_ajax_page: str
) -> HTML:
    with output_funnel.plugged():
        show_filter_form(info_list, context, page_name, reset_ajax_page)
        return HTML(output_funnel.drain())


def show_filter_form(
    info_list: List[InfoName], context: VisualContext, page_name: str, reset_ajax_page: str
) -> None:
    html.show_user_errors()
    html.begin_form("filter", method="GET", add_transid=False)
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
    )


def _show_filter_form_buttons(
    varprefix: str,
    filter_list_id: str,
    page_request_vars: Optional[Dict[str, Any]],
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
class VisualFilter(ValueSpec):
    def __init__(self, name, **kwargs):
        self._name = name
        self._filter = filter_registry[name]

        ValueSpec.__init__(self, **kwargs)

    def title(self):
        return self._filter.title

    def canonical_value(self) -> FilterHTTPVariables:
        return {}

    def render_input(self, varprefix: str, value: FilterHTTPVariables) -> None:
        # A filter can not be used twice on a page, because the varprefix is not used
        show_filter(self._filter, value)

    def from_html_vars(self, varprefix: str) -> FilterHTTPVariables:
        # A filter can not be used twice on a page, because the varprefix is not used
        return self._filter.value()

    def validate_datatype(self, value: Any, varprefix: str) -> None:
        if not isinstance(value, dict):
            raise MKUserError(
                varprefix, _("The value must be of type dict, but it has type %s") % type(value)
            )

    def validate_value(self, value: FilterHTTPVariables, varprefix: str) -> None:
        self._filter.validate_value(value)

    def value_to_html(self, value: FilterHTTPVariables) -> ValueSpecText:
        raise NotImplementedError()  # FIXME! Violates LSP!

    def value_to_json(self, value: FilterHTTPVariables) -> JSONValue:
        raise NotImplementedError()  # FIXME! Violates LSP!

    def value_from_json(self, json_value: JSONValue) -> FilterHTTPVariables:
        raise NotImplementedError()  # FIXME! Violates LSP!


def _single_info_selection_forth(restrictions: Sequence[str]) -> Tuple[str, Sequence[str]]:
    if not restrictions:
        choice_name = "no_restriction"
    elif restrictions == ["host"]:
        choice_name = "single_host"
    else:
        choice_name = "manual_selection"
    return choice_name, restrictions


def _single_info_selection_back(name_and_restrictions: Tuple[str, Sequence[str]]) -> Sequence[str]:
    return name_and_restrictions[1]


def SingleInfoSelection(info_keys: List[InfoName]) -> Transform:
    infos = [visual_info_registry[key]() for key in info_keys]
    manual_choices = [
        (i.ident, _("Show information of a single %s") % i.title)
        for i in sorted(infos, key=lambda inf: (inf.sort_index, inf.title))
    ]

    cascading_dropdown_choices: List[Tuple[str, str, ValueSpec]] = [
        (
            "no_restriction",
            _("No restrictions to specific objects"),
            FixedValue(
                [],
                totext="",
            ),
        ),
    ]

    if any(manual_choice[0] == "host" for manual_choice in manual_choices):
        cascading_dropdown_choices.append(
            (
                "single_host",
                _("Restrict to a single host"),
                FixedValue(
                    ["host"],
                    totext="",
                ),
            ),
        )

    cascading_dropdown_choices.append(
        (
            "manual_selection",
            _("Configure restrictions manually"),
            DualListChoice(
                title=_("Specific objects"),
                choices=manual_choices,
                rows=10,
                allow_empty=False,
            ),
        ),
    )

    # We need these transformations because the code which further processes the user input to this
    # valuespec expects a list of strings (since this was once the DualListChoice now located under
    # "manual_selection").
    return Transform(
        CascadingDropdown(
            choices=cascading_dropdown_choices,
            title=_("Specific objects"),
            sorted=False,
        ),
        back=_single_info_selection_back,
        forth=_single_info_selection_forth,
    )


# Converts a context from the form { filtername : { ... } } into
# the for { infoname : { filtername : { } } for editing.
def pack_context_for_editing(
    visual: Visual, info_handler: Optional[Callable[[Visual], List[InfoName]]]
) -> Dict:
    # We need to pack all variables into dicts with the name of the
    # info. Since we have no mapping from info the the filter variable,
    # we pack into every info every filter. The dict valuespec will
    # pick out what it needs. Yurks.
    packed_context = {}
    info_keys = info_handler(visual) if info_handler else visual_info_registry.keys()
    for info_name in info_keys:
        packed_context[info_name] = visual.get("context", {})
    return packed_context


def unpack_context_after_editing(packed_context: Dict) -> VisualContext:
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


def visual_page_breadcrumb(what: str, title: str, page_name: str) -> Breadcrumb:
    breadcrumb = make_main_menu_breadcrumb(mega_menu_registry.menu_customize())

    list_title = visual_type_registry[what]().plural_title
    breadcrumb.append(BreadcrumbItem(title=list_title.title(), url="edit_%s.py" % what))

    if page_name == "list":  # The list is the parent of all others
        return breadcrumb

    breadcrumb.append(BreadcrumbItem(title=title, url=makeuri(request, [])))
    return breadcrumb


def is_single_site_info(info_key: InfoName) -> bool:
    return visual_info_registry[info_key]().single_site


def single_infos_spec(single_infos: SingleInfos) -> Tuple[str, FixedValue]:
    return (
        "single_infos",
        FixedValue(
            single_infos,
            title=_("Show information of single"),
            totext=single_infos
            and ", ".join(single_infos)
            or _("Not restricted to showing a specific object."),
        ),
    )


def get_missing_single_infos(single_infos: SingleInfos, context: VisualContext) -> Set[FilterName]:
    return missing_context_filters(get_single_info_keys(single_infos), context)


def missing_context_filters(
    require_filters: Set[FilterName], context: VisualContext
) -> Set[FilterName]:
    set_filters = (
        filter_name
        for filter_name, filter_context in context.items()
        if any(filter_context.values())
    )

    return require_filters.difference(set_filters)


def visual_title(
    what: VisualTypeName, visual: Visual, context: VisualContext, skip_title_context: bool = False
) -> str:
    title = _u(visual["title"])

    # In case we have a site context given replace the $SITE$ macro in the titles.
    site_filter_vars = context.get("site", {})
    assert isinstance(site_filter_vars, dict)
    title = title.replace("$SITE$", site_filter_vars.get("site", ""))

    if visual["add_context_to_title"] and not skip_title_context:
        title = _add_context_title(context, visual["single_infos"], title)

    # Execute title plugin functions which might be added by the user to
    # the visuals plugins. When such a plugin function returns None, the regular
    # title of the page is used, otherwise the title returned by the plugin
    # function is used.
    for func in title_functions:
        result = func(what, visual, title)
        if result is not None:
            return result

    return title


def _add_context_title(context: VisualContext, single_infos: List[str], title: str) -> str:
    def filter_heading(
        filter_name: FilterName,
        filter_vars: FilterHTTPVariables,
    ) -> Optional[str]:
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
        # Disable 'wato_folder' filter, if WATO is disabled or there is a single host view
        if fn == "wato_folder" and (not config.wato_enabled or "host" in single_infos):
            continue

        if heading := filter_heading(fn, context.get(fn, {})):
            title = heading + " - " + title

    return title


# Determines the names of HTML variables to be set in order to
# specify a specify row in a datasource with a certain info.
# Example: the info "history" (Event Console History) needs
# the variables "event_id" and "history_line" to be set in order
# to exactly specify one history entry.
def info_params(info_key: InfoName) -> List[FilterName]:
    return [key for key, _vs in visual_info_registry[info_key]().single_spec]


def get_single_info_keys(single_infos: SingleInfos) -> Set[FilterName]:
    return set(chain.from_iterable(map(info_params, single_infos)))


def get_singlecontext_vars(context: VisualContext, single_infos: SingleInfos) -> Dict[str, str]:
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


def may_add_site_hint(
    visual_name: str,
    info_keys: List[InfoName],
    single_info_keys: SingleInfos,
    filter_names: List[FilterName],
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
    if visual_name in ["servicedesc", "servicedescpnp"]:
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


@cmk.gui.pages.register("ajax_popup_add_visual")
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
                html.write_text("Unhandled entry type '%s': %s" % (type(entry.item), entry.name))
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


def page_menu_dropdown_add_to_visual(add_type: str, name: str) -> List[PageMenuDropdown]:
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
def _encode_page_context(page_context: Dict) -> Dict:
    return {k: "" if v is None else v for k, v in page_context.items()}


def set_page_context(page_context: VisualContext) -> None:
    g.page_context = page_context


@cmk.gui.pages.register("ajax_add_visual")
def ajax_add_visual() -> None:
    visual_type_name = request.get_str_input_mandatory("visual_type")  # dashboards / views / ...
    visual_type = visual_type_registry[visual_type_name]()

    visual_name = request.get_str_input_mandatory("visual_name")  # add to this visual

    # type of the visual to add (e.g. view)
    element_type = request.get_str_input_mandatory("type")

    create_info_raw = request.get_str_input_mandatory("create_info")

    create_info = json.loads(create_info_raw)
    visual_type.add_visual_handler(
        visual_name, element_type, create_info["context"], create_info["params"]
    )
