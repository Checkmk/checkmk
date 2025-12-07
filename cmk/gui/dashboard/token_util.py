#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
from collections.abc import Callable, Generator

from cmk.ccc.exceptions import MKException
from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.dashboard.store import DashboardStore
from cmk.gui.dashboard.type_defs import DashboardConfig, DashletConfig
from cmk.gui.exceptions import HTTPRedirect, MKMethodNotAllowed, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.pages import PageContext, PageResult
from cmk.gui.session import UserContext
from cmk.gui.token_auth import (
    AuthToken,
    DashboardToken,
    get_token_store,
    TokenAuthenticatedPage,
    TokenId,
)
from cmk.gui.type_defs import ViewSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.views.store import ViewStore


class InvalidWidgetError(MKException):
    def __init__(
        self,
        disable_token: bool = False,
    ) -> None:
        self.disable_token = disable_token

    def __str__(self) -> str:
        return _("The given widget id does not match any of this dashboard's widgets.")


class DashboardTokenAuthenticatedPage(TokenAuthenticatedPage):
    def get(self, token: AuthToken, ctx: PageContext) -> PageResult:
        return self.__handle_method(token, ctx, self._get)

    def post(self, token: AuthToken, ctx: PageContext) -> PageResult:
        return self.__handle_method(token, ctx, self._post)

    @staticmethod
    def __check_token_details(token: AuthToken) -> DashboardToken:
        if not isinstance(token.details, DashboardToken) or token.details.disabled:  # type: ignore[redundant-expr]
            raise MKUserError(
                "cmk-token",
                _("The provided token is not valid for dashboard access."),
            )
        return token.details

    def _disable_and_redirect(self, token: AuthToken) -> PageResult:
        """Disable the token and redirect to the shared dashboard page.

        Redirection should then show the user a message that the token has been disabled."""
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

    def __handle_method(
        self,
        token: AuthToken,
        ctx: PageContext,
        inner: Callable[[AuthToken, DashboardToken, PageContext], PageResult],
    ) -> PageResult:
        try:
            self._before_method_handler(ctx)
            token_details = self.__check_token_details(token)
            return inner(token, token_details, ctx)

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


class ImpersonatedDashboardTokenIssuer:
    """Context for impersonating the issuer of a dashboard token.

    **DO NOT** construct this class directly, instead use the `impersonate_dashboard_token_issuer`
    context manager.
    """

    def __init__(self, token_details: DashboardToken, user_permissions: UserPermissions) -> None:
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
            permitted = visuals.available_by_owner("dashboards", store.all, self._user_permissions)
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
        x = ImpersonatedDashboardTokenIssuer(token_details, user_permissions)
        try:
            yield x
        finally:
            x.invalidate()


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
