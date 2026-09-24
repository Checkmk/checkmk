#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import assert_never

import cmk.web.utils.permission_verification as permissions
from cmk.gui import visuals
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.visuals.type import visual_type_registry
from cmk.livestatus_client import MKLivestatusException

from ..dashlet import Dashlet, dashlet_registry
from ..exceptions import WidgetRenderError
from ..token_util import (
    disable_dashboard_token_by_id,
    get_dashboard_widget_by_id,
    impersonate_dashboard_token_issuer,
    InvalidWidgetError,
)
from ..type_defs import DashletConfig
from ._contextual_link_encoding import EffectiveLink
from ._utils import validated_dashboard_token
from .model.contextual_link import (
    ContextualLinkDefault,
    ContextualLinkInherited,
    ContextualLinkNone,
    VisualLocation,
)
from .model.widget_content._base import BaseWidgetContent
from .model.widget_source import ExplicitWidgetContent, SavedWidgetContent

PERMISSIONS_WIDGET_QUERY = permissions.AllPerm(
    [
        permissions.Optional(permissions.Perm("general.see_all")),
        permissions.Optional(permissions.Perm("bi.see_all")),
        permissions.Optional(permissions.OkayToIgnorePerm("mkeventd.seeall")),
        permissions.Optional(permissions.OkayToIgnorePerm("mkeventd.seeunrelated")),
        permissions.Optional(
            permissions.AllPerm(
                [
                    permissions.Perm("general.edit_dashboards"),
                    permissions.Perm("general.see_user_dashboards"),
                    permissions.Perm("general.see_packaged_dashboards"),
                    permissions.Perm("general.edit_foreign_dashboards"),
                    permissions.PrefixPerm("dashboard"),
                ]
            )
        ),
    ]
)

PERMISSIONS_LINK_TARGET = permissions.Optional(
    permissions.AllPerm(
        [
            permissions.Perm("general.edit_views"),
            permissions.Perm("general.see_user_views"),
            permissions.Perm("general.see_packaged_views"),
            permissions.PrefixPerm("view"),
        ]
    )
)


@dataclass(frozen=True)
class ResolvedWidget:
    config: DashletConfig
    context: VisualContext
    infos: SingleInfos
    widget: Dashlet[DashletConfig]
    links: Sequence[EffectiveLink]


@contextmanager
def resolve_widget[C: BaseWidgetContent](
    api_context: ApiContext,
    source: ExplicitWidgetContent[C] | SavedWidgetContent,
    accepted_types: frozenset[str],
    built_in_link: Callable[[C], EffectiveLink | None],
) -> Iterator[ResolvedWidget]:
    """Resolve the widget a request names, and translate the failures of its computation."""
    try:
        with _resolve(api_context, source, accepted_types, built_in_link) as widget:
            yield widget
    except (MKMissingDataError, MKUserError, WidgetRenderError) as exc:
        raise ProblemException(status=404, title="No data available", detail=str(exc)) from exc
    except MKLivestatusException as exc:
        raise ProblemException(
            status=503, title="Monitoring data source unavailable", detail=str(exc)
        ) from exc


@contextmanager
def _resolve[C: BaseWidgetContent](
    api_context: ApiContext,
    source: ExplicitWidgetContent[C] | SavedWidgetContent,
    accepted_types: frozenset[str],
    built_in_link: Callable[[C], EffectiveLink | None],
) -> Iterator[ResolvedWidget]:
    if isinstance(source, SavedWidgetContent):
        with _resolve_saved(api_context, source, accepted_types) as resolved:
            yield resolved
        return

    if api_context.token is not None:
        raise ProblemException(
            status=403,
            title="Forbidden",
            detail="A token caller may only name a saved widget.",
        )
    _check_accepted(source.content.internal_type(), accepted_types)
    config = source.content.to_internal()
    widget = _dashlet(config, source.context)
    yield ResolvedWidget(
        config=config,
        context=source.context,
        infos=widget.infos(),
        widget=widget,
        links=_effective_links(
            source.content, built_in_link(source.content), api_context.config.user_permissions()
        ),
    )


@contextmanager
def _resolve_saved(
    api_context: ApiContext, source: SavedWidgetContent, accepted_types: frozenset[str]
) -> Iterator[ResolvedWidget]:
    token, token_details = validated_dashboard_token(api_context.token)
    try:
        with impersonate_dashboard_token_issuer(
            token.issuer, token_details, api_context.config.user_permissions()
        ) as issuer:
            dashboard = issuer.load_dashboard()
            config = get_dashboard_widget_by_id(dashboard, source.widget_id)
            if config["type"] not in dashlet_registry:
                raise InvalidWidgetError(disable_token=True)
            _check_accepted(config["type"], accepted_types)
            context = visuals.get_merged_context(
                dashboard.get("context", {}), config.get("context", {})
            )
            widget = _dashlet(config, context)
            yield ResolvedWidget(
                config=config, context=context, infos=widget.infos(), widget=widget, links=[]
            )
    except InvalidWidgetError as exc:
        if exc.disable_token:
            disable_dashboard_token_by_id(token.token_id)
        raise ProblemException(status=404, title="Widget not found", detail=str(exc)) from exc


def _check_accepted(internal_type: str, accepted_types: frozenset[str]) -> None:
    if internal_type not in accepted_types:
        raise ProblemException(
            status=400,
            title="Widget type not supported",
            detail=f"This endpoint does not compute widgets of the type {internal_type!r}.",
        )


def _dashlet(config: DashletConfig, context: VisualContext) -> Dashlet[DashletConfig]:
    return dashlet_registry[config["type"]](config, base_context=context)


def _effective_links(
    content: BaseWidgetContent,
    built_in_link: EffectiveLink | None,
    user_permissions: UserPermissions,
) -> list[EffectiveLink]:
    match content.configured_contextual_link():
        case ContextualLinkNone():
            return []
        case ContextualLinkInherited() as inherited:
            return [
                EffectiveLink(
                    title=_target_title(inherited.location, user_permissions),
                    location=inherited.location,
                    include_context=inherited.include_context,
                    include_time_range=inherited.include_time_range,
                    show_filter_form=inherited.show_filter_form,
                )
            ]
        case ContextualLinkDefault() | ApiOmitted():
            return [] if built_in_link is None else [built_in_link]
        case unreachable:
            assert_never(unreachable)


def _target_title(location: VisualLocation, user_permissions: UserPermissions) -> str:
    visual_type = visual_type_registry[location.type]()
    visual = visual_type.permitted_visuals(visual_type.visuals(), user_permissions).get(
        location.name
    )
    if visual is None:
        return location.name
    return visuals.visual_title(location.type, visual, {}, skip_title_context=True)
