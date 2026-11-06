#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus
from typing import assert_never, Protocol, TypeIs

import cmk.web.utils.permission_verification as permissions
from cmk.gui import visuals
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client import MKLivestatusException

from ..dashlet import dashlet_registry
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
from .model.context_filters import context_filter_to_internal
from .model.contextual_link import (
    ContextualLinkCustom,
    ContextualLinkDefault,
    ContextualLinkInherited,
    ContextualLinkNone,
    resolved_copy,
)
from .model.link_properties import ResolvedLink
from .model.widget_content import content_from_internal
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


class AcceptsContent[C: BaseWidgetContent](Protocol):
    """Whether an endpoint computes a widget with this content."""

    def __call__(self, content: BaseWidgetContent, /) -> TypeIs[C]: ...


@dataclass(frozen=True)
class ResolvedWidget[C: BaseWidgetContent]:
    content: C
    context: VisualContext
    infos: SingleInfos
    links: Sequence[EffectiveLink]

    def links_to_api(self) -> list[ResolvedLink]:
        """The links of the widget in their API representation."""
        return [link.to_api() for link in self.links]


def no_built_in_link(_content: BaseWidgetContent, _context: VisualContext) -> None:
    """The built-in link of a widget type that links nowhere by default."""


@contextmanager
def resolve_widget[C: BaseWidgetContent](
    api_context: ApiContext,
    source: ExplicitWidgetContent[C] | SavedWidgetContent,
    accepts: AcceptsContent[C],
    built_in_link: Callable[[C, VisualContext], EffectiveLink | None],
) -> Iterator[ResolvedWidget[C]]:
    """Resolve the widget a request names, and translate the failures of its computation."""
    with _translated_failures():
        if isinstance(source, SavedWidgetContent):
            with _resolve_saved(api_context, source, accepts) as widget:
                yield widget
        else:
            yield _resolve_explicit(api_context, source, built_in_link)


@contextmanager
def resolve_saved_widget[C: BaseWidgetContent](
    api_context: ApiContext,
    source: SavedWidgetContent,
    accepts: AcceptsContent[C],
) -> Iterator[ResolvedWidget[C]]:
    """Resolve a widget of the token's dashboard, and translate the failures of its computation."""
    with _translated_failures(), _resolve_saved(api_context, source, accepts) as widget:
        yield widget


@contextmanager
def _translated_failures() -> Iterator[None]:
    try:
        yield
    except (MKMissingDataError, MKUserError, WidgetRenderError) as exc:
        raise ProblemException(
            status=HTTPStatus.NOT_FOUND, title="No data available", detail=str(exc)
        ) from exc
    except MKLivestatusException as exc:
        raise ProblemException(
            status=HTTPStatus.SERVICE_UNAVAILABLE,
            title="Monitoring data source unavailable",
            detail=str(exc),
        ) from exc


def _resolve_explicit[C: BaseWidgetContent](
    api_context: ApiContext,
    source: ExplicitWidgetContent[C],
    built_in_link: Callable[[C, VisualContext], EffectiveLink | None],
) -> ResolvedWidget[C]:
    if api_context.token is not None:
        raise ProblemException(
            status=HTTPStatus.FORBIDDEN,
            title="Forbidden",
            detail="A token caller may only name a saved widget.",
        )
    return resolve_viewed_widget(
        source.content, source.context, api_context.config.user_permissions(), built_in_link
    )


def resolve_viewed_widget[C: BaseWidgetContent](
    content: C,
    context: VisualContext,
    user_permissions: UserPermissions,
    built_in_link: Callable[[C, VisualContext], EffectiveLink | None],
) -> ResolvedWidget[C]:
    """Resolve a widget the logged-in user views, with the links the user may follow."""
    return ResolvedWidget(
        content=content,
        context=context,
        infos=_infos(content.to_internal(), context),
        links=_effective_links(content, built_in_link(content, context), user_permissions),
    )


@contextmanager
def _resolve_saved[C: BaseWidgetContent](
    api_context: ApiContext,
    source: SavedWidgetContent,
    accepts: AcceptsContent[C],
) -> Iterator[ResolvedWidget[C]]:
    token, token_details = validated_dashboard_token(api_context.token)
    try:
        with impersonate_dashboard_token_issuer(
            token.issuer, token_details, api_context.config.user_permissions()
        ) as issuer:
            dashboard = issuer.load_dashboard()
            config = get_dashboard_widget_by_id(dashboard, source.widget_id)
            if config["type"] not in dashlet_registry:
                raise InvalidWidgetError(disable_token=True)
            content = _accepted_content(config, accepts)
            context = visuals.get_merged_context(
                dashboard.get("context", {}), config.get("context", {})
            )
            yield ResolvedWidget(
                content=content, context=context, infos=_infos(config, context), links=[]
            )
    except InvalidWidgetError as exc:
        if exc.disable_token:
            disable_dashboard_token_by_id(token.token_id)
        raise ProblemException(
            status=HTTPStatus.NOT_FOUND, title="Widget not found", detail=str(exc)
        ) from exc


def _accepted_content[C: BaseWidgetContent](config: DashletConfig, accepts: AcceptsContent[C]) -> C:
    if accepts(content := content_from_internal(config)):
        return content
    raise ProblemException(
        status=HTTPStatus.BAD_REQUEST,
        title="Widget type not supported",
        detail=f"This endpoint does not compute widgets of the type {config['type']!r}.",
    )


def _infos(config: DashletConfig, context: VisualContext) -> SingleInfos:
    return dashlet_registry[config["type"]](config, base_context=context).infos()


def _effective_links(
    content: BaseWidgetContent,
    built_in_link: EffectiveLink | None,
    user_permissions: UserPermissions,
) -> list[EffectiveLink]:
    """The widget's links, without a configured one to a page the viewer cannot open."""
    match content.configured_contextual_link():
        case ContextualLinkNone():
            return []
        case ContextualLinkInherited() as inherited:
            if (target := resolved_copy(inherited.location, user_permissions)) is None:
                return []
            return [
                EffectiveLink(
                    title=visuals.visual_title_without_context(target, {}),
                    location=inherited.location,
                    include_context=inherited.include_context,
                    include_time_range=inherited.include_time_range,
                    show_filter_form=inherited.show_filter_form,
                )
            ]
        case ContextualLinkCustom() as custom:
            return [
                EffectiveLink(
                    title=entry.title,
                    location=entry.location,
                    include_context=entry.include_context,
                    include_time_range=entry.include_time_range,
                    show_filter_form=entry.show_filter_form,
                    filters=[context_filter_to_internal(f) for f in entry.filters],
                )
                for entry in custom.links
                if resolved_copy(entry.location, user_permissions) is not None
            ]
        case ContextualLinkDefault():
            return [] if built_in_link is None else [built_in_link]
        case unreachable:
            assert_never(unreachable)
