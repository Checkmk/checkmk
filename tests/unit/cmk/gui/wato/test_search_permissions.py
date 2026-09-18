#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from livestatus import SiteConfigurations

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.wato._search_permissions import SetupPermissionsHandler
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


@pytest.fixture(name="config")
def fixture_config() -> Config:
    return Config()


@pytest.fixture(name="http_request")
def fixture_http_request() -> Request:
    return Request(create_environ())


class TestPermissionHandler:
    @pytest.fixture(name="created_host_url")
    def fixture_created_host_url(self) -> str:
        folder = folder_tree().root_folder()
        folder.create_hosts(
            [(HostName("host"), {}, [])],
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
            acting_user=user,
        )
        return "wato.py?folder=&host=host&mode=edit_host"

    @pytest.mark.usefixtures("with_admin_login")
    def test_may_see_category(
        self, config: Config, http_request: Request, test_edition: Edition
    ) -> None:
        permissions_handler = SetupPermissionsHandler(
            test_edition, PageContext(config=config, request=http_request)
        )
        for category in permissions_handler._category_permissions:  # noqa: SLF001
            assert permissions_handler.may_see_category(category)

    @pytest.mark.usefixtures("request_context")
    def test_may_see_url_false(
        self, config: Config, http_request: Request, test_edition: Edition
    ) -> None:
        permissions_handler = SetupPermissionsHandler(
            test_edition, PageContext(config=config, request=http_request)
        )
        visibility_check = permissions_handler.get_visibility_check("setup")
        assert not visibility_check("wato.py?folder=&mode=service_groups")

    @pytest.mark.usefixtures("with_admin_login")
    def test_may_see_url_true(
        self, config: Config, http_request: Request, test_edition: Edition
    ) -> None:
        permissions_handler = SetupPermissionsHandler(
            test_edition, PageContext(config=config, request=http_request)
        )
        visibility_check = permissions_handler.get_visibility_check("setup")
        assert visibility_check("wato.py?folder=&mode=service_groups")

    @pytest.mark.usefixtures("with_admin_login")
    def test_may_see_url_host_true(
        self, config: Config, created_host_url: str, test_edition: Edition
    ) -> None:
        # NOTE: unfortunately, a test request fixture is difficult to create here since the host and
        # folders code relies heavily on adapting the global request proxy. For now, we will just
        # import the global proxy here explicitly as it's implicitly shared by the
        # `created_host_url` fixture.
        from cmk.gui.http import request

        permissions_handler = SetupPermissionsHandler(
            test_edition, PageContext(config=config, request=request)
        )
        visibility_check = permissions_handler.get_visibility_check("setup")
        assert visibility_check(created_host_url)

    @pytest.mark.usefixtures("with_admin_login")
    def test_may_see_url_host_false(
        self,
        config: Config,
        http_request: Request,
        created_host_url: str,
        test_edition: Edition,
    ) -> None:
        # NOTE: the created host is not visible because it was not created with the passed request
        # context. This is because the host and folders code relies heavily on adapting the global
        # request proxy.
        permissions_handler = SetupPermissionsHandler(
            test_edition, PageContext(config=config, request=http_request)
        )
        visibility_check = permissions_handler.get_visibility_check("setup")
        assert not visibility_check(created_host_url)
