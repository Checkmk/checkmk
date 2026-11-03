#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ._compute_endpoint import widget_compute_endpoint
from ._contextual_link_encoding import (
    EffectiveLink,
    link_columns,
    link_properties_for,
    view_link,
    with_link_columns,
)
from ._family import DASHBOARD_FAMILY
from ._registration import register_endpoints
from ._utils import (
    clone_dashboard_config,
    convert_internal_relative_dashboard_to_api_model_dict,
    dashboard_owner_description,
    DashboardConstants,
    DashboardOwnerWithBuiltin,
    get_dashboard_for_read,
    get_permitted_user_id,
    INTERNAL_TO_API_TYPE_NAME,
    make_pending_changes,
    PERMISSIONS_DASHBOARD,
    PERMISSIONS_DASHBOARD_EDIT,
    PERMISSIONS_DASHBOARD_READ,
    save_dashboard_to_file,
    validated_dashboard_token,
)
from ._widget_resolution import (
    no_built_in_link,
    PERMISSIONS_LINK_TARGET,
    PERMISSIONS_WIDGET_QUERY,
    resolve_saved_widget,
    resolve_widget,
    ResolvedWidget,
)
from .model.contextual_link import ContextualLinkSpec
from .model.link_properties import LinkProperties, ResolvedLink
from .model.widget_content._base import BaseWidgetContent
from .model.widget_source import ExplicitWidgetContent, SavedWidgetContent, WidgetTimeRange

__all__ = [
    "BaseWidgetContent",
    "ContextualLinkSpec",
    "DASHBOARD_FAMILY",
    "DashboardConstants",
    "DashboardOwnerWithBuiltin",
    "EffectiveLink",
    "ExplicitWidgetContent",
    "INTERNAL_TO_API_TYPE_NAME",
    "LinkProperties",
    "PERMISSIONS_DASHBOARD",
    "PERMISSIONS_DASHBOARD_EDIT",
    "PERMISSIONS_DASHBOARD_READ",
    "PERMISSIONS_LINK_TARGET",
    "PERMISSIONS_WIDGET_QUERY",
    "ResolvedLink",
    "ResolvedWidget",
    "SavedWidgetContent",
    "WidgetTimeRange",
    "clone_dashboard_config",
    "convert_internal_relative_dashboard_to_api_model_dict",
    "dashboard_owner_description",
    "get_dashboard_for_read",
    "get_permitted_user_id",
    "link_properties_for",
    "make_pending_changes",
    "no_built_in_link",
    "register_endpoints",
    "resolve_saved_widget",
    "resolve_widget",
    "save_dashboard_to_file",
    "validated_dashboard_token",
    "view_link",
    "widget_compute_endpoint",
    "link_columns",
    "with_link_columns",
]
