#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import datetime as dt
import json
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import cast, override

from dateutil.relativedelta import relativedelta

from cmk.ccc.exceptions import MKException
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition, edition
from cmk.gui import visuals
from cmk.gui.dashboard.store import DashboardStore
from cmk.gui.dashboard.type_defs import DashboardConfig, DashletConfig, LinkedViewDashletConfig
from cmk.gui.exceptions import HTTPRedirect, MKMethodNotAllowed, MKMissingDataError, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext, PageResult
from cmk.gui.session import UserContext
from cmk.gui.token_auth import (
    AuthToken,
    DashboardToken,
    get_token_store,
    TokenAuthenticatedPage,
    TokenId,
    TokenStore,
)
from cmk.gui.type_defs import ViewSpec
from cmk.gui.utils.json import CustomObjectJSONEncoder
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.views.store import get_permitted_views, ViewStore
from cmk.utils import paths


class InvalidWidgetError(MKException):
    def __init__(
        self,
        disable_token: bool = False,
    ) -> None:
        self.disable_token = disable_token

    @override
    def __str__(self) -> str:
        return _("The given widget ID does not match any of this dashboard's widgets.")


class InvalidDashboardTokenReference(MKException):
    """The token ID referenced in the dashboard configuration is invalid."""


class DashboardTokenNotFound(MKUserError):
    """The dashboard doesn't have a token assigned to it."""


class DashboardTokenAlreadyExists(MKUserError):
    """The dashboard already has a token assigned to it."""


class DashboardTokenExpirationInvalid(MKUserError):
    """The token expiration time is invalid."""


def max_expiration_time_community_edition(now: dt.datetime) -> dt.datetime:
    """Get the maximum expiration time for dashboard tokens in the Community Edition."""
    maximum = now + dt.timedelta(days=31)
    return maximum.replace(hour=23, minute=59, second=59, microsecond=999999)


def _validate_expiration(
    now: dt.datetime, expiration_time: dt.datetime | None, *, allow_past: bool = False
) -> dt.datetime | None:
    """Validate the given expiration time for a dashboard token."""
    if not allow_past and expiration_time is not None and expiration_time <= now:
        raise DashboardTokenExpirationInvalid(
            varname="expiration_time",
            message=_("The expiration time must be in the future."),
        )

    if edition(paths.omd_root) == Edition.COMMUNITY:
        # please consider buying commercial editions :)
        upper_bound = max_expiration_time_community_edition(now)
        if expiration_time is None or expiration_time > upper_bound:
            raise DashboardTokenExpirationInvalid(
                varname="expiration_time",
                message=_(
                    "In the Checkmk Community Edition, dashboard tokens can only be valid for up to one month."
                ),
            )

    return expiration_time


@contextmanager
def edit_dashboard_auth_token(
    dashboard: DashboardConfig, token_store: TokenStore | None = None
) -> Generator[tuple[AuthToken, DashboardToken]]:
    """Context manager to edit the auth token of a dashboard."""
    if (token_id := dashboard.get("public_token_id")) is None:
        raise DashboardTokenNotFound(
            varname=None,
            message=_("No token for this dashboard exists."),
            status=404,
        )

    if token_store is None:
        token_store = get_token_store()
    with token_store.read_locked() as data:
        if (token := data.get(TokenId(token_id))) and isinstance(token.details, DashboardToken):
            yield token, token.details
            return

    raise InvalidDashboardTokenReference()


def get_dashboard_auth_token(
    dashboard: DashboardConfig, token_store: TokenStore | None = None
) -> AuthToken | None:
    """Read access to the auth token of a dashboard."""
    try:
        with edit_dashboard_auth_token(dashboard, token_store) as (token, _details):
            return token
    except (DashboardTokenNotFound, InvalidDashboardTokenReference):
        return None


def disable_dashboard_token(
    dashboard_config: DashboardConfig, token_store: TokenStore | None = None
) -> None:
    """Disable the auth token of a dashboard.

    This should be done whenever a dashboard is edited."""
    try:
        with edit_dashboard_auth_token(dashboard_config, token_store) as (_token, details):
            details.disabled = True
    except (DashboardTokenNotFound, InvalidDashboardTokenReference):
        return None


def issue_dashboard_token(
    dashboard: DashboardConfig,
    expiration_time: dt.datetime | None,
    comment: str = "",
    token_store: TokenStore | None = None,
) -> AuthToken:
    """Issues a new dashboard token for the given dashboard."""
    if dashboard.get("public_token_id"):
        raise DashboardTokenAlreadyExists(
            varname=None,
            message=_("A token for this dashboard already exists, cannot create another one."),
        )

    if token_store is None:
        token_store = get_token_store()
    now = dt.datetime.now(dt.UTC)
    expiration_time = _validate_expiration(now, expiration_time)
    return token_store.issue(
        DashboardToken(
            type_="dashboard",
            owner=dashboard["owner"],
            dashboard_name=dashboard["name"],
            comment=comment,
            disabled=False,
            view_owners=_get_view_owners(dashboard),
            synced_at=now,
        ),
        issuer=user.ident,
        now=now,
        valid_for=relativedelta(expiration_time, now) if expiration_time else None,
    )


def update_dashboard_token(
    dashboard: DashboardConfig,
    disabled: bool,
    expiration_time: dt.datetime | None,
    comment: str,
    token_store: TokenStore | None = None,
) -> AuthToken:
    """Update an existing dashboard token for the given dashboard."""
    now = dt.datetime.now(dt.UTC)
    expiration_time = _validate_expiration(now, expiration_time, allow_past=True)
    with edit_dashboard_auth_token(dashboard, token_store) as (token, details):
        token.valid_until = expiration_time
        # name should be updated, just in case there was a rename
        details.dashboard_name = dashboard["name"]
        details.owner = dashboard["owner"]
        details.comment = comment
        details.disabled = disabled
        details.view_owners = _get_view_owners(dashboard)
        details.synced_at = now
        return token


def _get_view_owners(dashboard_config: DashboardConfig) -> dict[str, UserId]:
    """Get the owners of all views used in linked view widgets of the dashboard.

    This is relative to the current user and their permissions."""
    widget_id_to_view_name = {
        f"{dashboard_config['name']}-{idx}": cast(LinkedViewDashletConfig, widget)["name"]
        for idx, widget in enumerate(dashboard_config["dashlets"])
        if widget["type"] == "linked_view"
    }
    view_owners: dict[str, UserId] = {}
    if widget_id_to_view_name:
        views = get_permitted_views()
        for widget_id, view_name in widget_id_to_view_name.items():
            if view_name in views:
                view_owners[widget_id] = views[view_name]["owner"]
            # else: a not found message should be displayed in the widget itself (on access)

    return view_owners


class DashboardTokenAuthenticatedPage(TokenAuthenticatedPage):
    @override
    def get(self, token: AuthToken, ctx: PageContext) -> PageResult:
        return self._handle_method(token, ctx, self._get)

    @override
    def post(self, token: AuthToken, ctx: PageContext) -> PageResult:
        return self._handle_method(token, ctx, self._post)

    @staticmethod
    def __check_token_details(token: AuthToken) -> DashboardToken:
        if not isinstance(token.details, DashboardToken) or token.details.disabled:
            raise MKUserError(
                "cmk-token",
                _("The provided token is not valid for dashboard access."),
            )
        return token.details

    def _disable_and_redirect(self, token: AuthToken) -> PageResult:
        """Disable the token and redirect to the shared dashboard page.

        Redirection should then show the user a message that the token has been disabled.
        """
        with get_token_store().read_locked() as store:
            if (edit_token := store.get(token.token_id)) and isinstance(
                edit_token.details, DashboardToken
            ):
                edit_token.details.disabled = True

        return self._redirect_to_shared_dashboard_page(token)

    def _redirect_to_shared_dashboard_page(self, token: AuthToken) -> PageResult:
        """Redirect to the shared dashboard page."""
        # NOTE: this must be handled by the widgets properly, otherwise they'll most likely just
        # display some error message because they can't handle the response.
        # That's fine for the v1 though, as long as the token is disabled beforehand.
        raise HTTPRedirect(get_shared_dashboard_url(token.token_id)) from None

    def _handle_method(
        self,
        token: AuthToken,
        ctx: PageContext,
        inner: Callable[[AuthToken, DashboardToken, PageContext], PageResult],
    ) -> PageResult:
        try:
            self._before_method_handler(ctx)
            token_details = self.__check_token_details(token)
            result = inner(token, token_details, ctx)
            return self._after_method_handler(result, ctx)

        except MKMethodNotAllowed:
            raise

        except InvalidWidgetError as e:
            if e.disable_token:
                self._disable_and_redirect(token)

            return self._handle_exception(e, ctx)

        except Exception as e:
            if isinstance(e, HTTPRedirect):
                raise
            return self._handle_exception(e, ctx)

    def _before_method_handler(self, ctx: PageContext) -> None:
        """Override this to implement any pre-method logic"""
        pass

    def _after_method_handler(self, result: PageResult, ctx: PageContext) -> PageResult:
        """Override this to implement any post-method logic"""
        return result

    def _handle_exception(self, exception: Exception, ctx: PageContext) -> PageResult:
        """Override this to implement custom exception handling logic"""
        html.write_html(html.render_message(str(exception)))
        return None

    def _get(self, token: AuthToken, token_details: DashboardToken, ctx: PageContext) -> PageResult:
        """Override this to implement GET method logic"""
        raise MKMethodNotAllowed("Method not supported")

    def _post(
        self, token: AuthToken, token_details: DashboardToken, ctx: PageContext
    ) -> PageResult:
        """Override this to implement POST method logic"""
        raise MKMethodNotAllowed("Method not supported")


class DashboardTokenAuthenticatedJsonPage(DashboardTokenAuthenticatedPage):
    @staticmethod
    def _set_response_data(data: dict[str, object]) -> None:
        response.set_data(json.dumps(data, cls=CustomObjectJSONEncoder))

    @override
    def _before_method_handler(self, ctx: PageContext) -> None:
        response.set_content_type("application/json")

    @override
    def _after_method_handler(self, result: PageResult, ctx: PageContext) -> PageResult:
        self._set_response_data({"result_code": 0, "result": result, "severity": "success"})
        return result

    @override
    def _handle_exception(self, exception: Exception, ctx: PageContext) -> None:
        if ctx.config.debug:
            raise exception

        severity = "error"
        if isinstance(exception, MKMissingDataError):
            severity = "success"

        self._set_response_data({"result_code": 1, "result": str(exception), "severity": severity})


class ImpersonatedDashboardTokenIssuer:
    """Context for impersonating the issuer of a dashboard token.

    **DO NOT** construct this class directly, instead use the `impersonate_dashboard_token_issuer`
    context manager.
    """

    def __init__(
        self, token_issuer: UserId, token_details: DashboardToken, user_permissions: UserPermissions
    ) -> None:
        self._token_issuer = token_issuer
        self._token_details = token_details
        self._user_permissions = user_permissions
        self.__invalidated: bool = False
        self.__dashboard_cache: DashboardConfig | None = None
        self.__permitted_views_cache: dict[str, ViewSpec] | None = None

    def invalidate(self) -> None:
        """Invalidate this context, preventing further use."""
        self.__invalidated = True

    def _check_valid(self) -> None:
        """Ensure the impersonation context is still valid."""
        if self.__invalidated:
            raise Exception("Impersonation context has already been exited.")

    def load_dashboard(self) -> DashboardConfig:
        """Load the dashboard associated with the given token."""
        self._check_valid()

        if self.__dashboard_cache is None:
            # due to caching within DashboardStore we can only safely take the `all` part
            # then we calculate the permitted dashboards again for the impersonated user
            store = DashboardStore.get_instance()

            # Administrative override for users who can edit foreign dashboards
            if self._user_permissions.user_may(
                self._token_issuer, "general.edit_foreign_dashboards"
            ):
                permitted: dict[str, dict[UserId, DashboardConfig]] = {}
                for (owner_id, dashboard_name), board in store.all.items():
                    permitted.setdefault(dashboard_name, {})[owner_id] = board
            else:
                permitted = visuals.available_by_owner(
                    "dashboards", store.all, self._user_permissions
                )

            try:
                self.__dashboard_cache = permitted[self._token_details.dashboard_name][
                    self._token_details.owner
                ]
            except KeyError:
                raise InvalidWidgetError(disable_token=True)

        return self.__dashboard_cache

    def _load_permitted_views(self) -> dict[str, ViewSpec]:
        """Get all permitted views for the impersonated user."""
        self._check_valid()

        if self.__permitted_views_cache is None:
            # due to caching within ViewStore we can only safely take the `all` part
            # then we calculate the permitted views again for the impersonated user
            store = ViewStore.get_instance()
            self.__permitted_views_cache = visuals.available(
                "views", store.all, self._user_permissions
            )

        return self.__permitted_views_cache

    def load_linked_view(self, view_name: str) -> ViewSpec:
        """Load a linked view by name.

        Rather than loading a view from a specific owner, we use the normal view resolution so that
        we can disable the token if changed permissions (or something else) cause us to find a view
        from a different owner than expected.
        """
        self._check_valid()

        permitted = self._load_permitted_views()
        try:
            return permitted[view_name]
        except KeyError:
            raise InvalidWidgetError(disable_token=True)


@contextlib.contextmanager
def impersonate_dashboard_token_issuer(
    token_issuer: UserId, token_details: DashboardToken, user_permissions: UserPermissions
) -> Generator[ImpersonatedDashboardTokenIssuer]:
    """Impersonate the token issuer for the duration of the context.

    The context yields an object which can be used to load user specific data."""
    with UserContext(token_issuer, user_permissions):
        issuer = ImpersonatedDashboardTokenIssuer(token_issuer, token_details, user_permissions)
        try:
            yield issuer
        finally:
            issuer.invalidate()


def get_dashboard_widget_by_id(dashboard_config: DashboardConfig, widget_id: str) -> DashletConfig:
    """Get the widget configuration for the given widget ID."""
    # TODO: once widgets are stored with their own IDs, this function should be removed
    widgets = {
        f"{dashboard_config['name']}-{idx}": widget_config
        for idx, widget_config in enumerate(dashboard_config["dashlets"])
    }
    if widget_config := widgets.get(widget_id):
        return widget_config

    raise InvalidWidgetError()


def get_shared_dashboard_url(token_id: TokenId) -> str:
    """Get the shared dashboard URL, in short form."""
    query_vars = urlencode_vars([("cmk-token", f"0:{token_id}")])
    return f"shared_dashboard.py?{query_vars}"
