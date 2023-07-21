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

from ._add_to_visual import ajax_add_visual, ajax_popup_add
from ._add_to_visual import page_menu_dropdown_add_to_visual as page_menu_dropdown_add_to_visual
from ._add_to_visual import set_page_context as set_page_context
from ._breadcrumb import visual_page_breadcrumb as visual_page_breadcrumb
from ._filter_context import active_context_from_request as active_context_from_request
from ._filter_context import context_to_uri_vars as context_to_uri_vars
from ._filter_context import filters_of_visual as filters_of_visual
from ._filter_context import get_context_from_uri_vars as get_context_from_uri_vars
from ._filter_context import get_filter as get_filter
from ._filter_context import get_filter_headers as get_filter_headers
from ._filter_context import get_link_filter_names as get_link_filter_names
from ._filter_context import get_merged_context as get_merged_context
from ._filter_context import get_missing_single_infos as get_missing_single_infos
from ._filter_context import get_single_info_keys as get_single_info_keys
from ._filter_context import get_singlecontext_vars as get_singlecontext_vars
from ._filter_context import info_params as info_params
from ._filter_context import missing_context_filters as missing_context_filters
from ._filter_context import visible_filters_of_visual as visible_filters_of_visual
from ._filter_form import render_filter_form as render_filter_form
from ._filter_form import show_filter_form as show_filter_form
from ._filter_valuespecs import FilterChoices as FilterChoices
from ._filter_valuespecs import PageAjaxVisualFilterListGetChoice
from ._filter_valuespecs import VisualFilterList as VisualFilterList
from ._filter_valuespecs import VisualFilterListWithAddPopup as VisualFilterListWithAddPopup
from ._page_create_visual import page_create_visual as page_create_visual
from ._page_create_visual import SingleInfoSelection as SingleInfoSelection
from ._page_edit_visual import get_context_specs as get_context_specs
from ._page_edit_visual import page_edit_visual as page_edit_visual
from ._page_edit_visual import process_context_specs as process_context_specs
from ._page_edit_visual import render_context_specs as render_context_specs
from ._page_edit_visual import single_infos_spec as single_infos_spec
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
from ._title import view_title as view_title
from ._title import visual_title as visual_title


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("ajax_visual_filter_list_get_choice")(
        PageAjaxVisualFilterListGetChoice
    )
    page_registry.register_page_handler("ajax_popup_add_visual", ajax_popup_add)
    page_registry.register_page_handler("ajax_add_visual", ajax_add_visual)


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
