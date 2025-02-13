#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides a class for managing web sessions with a Checkmk site.

It contains methods for handling HTTP requests, verifying HTML page resources, and
managing authentication.

Note: this implementation is purely request-based and does not manage cookies or running
JavaScript scripts.
"""

import logging
import os
import re
import urllib.parse
from collections.abc import Collection, Container
from http.cookiejar import Cookie

import requests
from bs4 import BeautifulSoup

from tests.testlib.version import version_from_env


class APIError(Exception):
    pass


logger = logging.getLogger()


class CMKWebSession:
    def __init__(self, site) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        # Resources are only fetched and verified once per session
        self.verified_resources: set = set()
        self.site = site
        self.session = requests.Session()

    def check_redirect(self, path: str, expected_target: str | None = None) -> None:
        response = self.get(path, expected_code=302, allow_redirects=False)
        if expected_target:
            if response.headers["Location"] != expected_target:
                raise AssertionError(
                    "REDIRECT FAILED: '{}' != '{}'".format(
                        response.headers["Location"], expected_target
                    )
                )
            assert response.headers["Location"] == expected_target

    def get(self, *args, **kwargs) -> requests.Response:  # type: ignore[no-untyped-def]
        return self.request("get", *args, **kwargs)

    def post(self, *args, **kwargs) -> requests.Response:  # type: ignore[no-untyped-def]
        return self.request("post", *args, **kwargs)

    def request(  # type: ignore[no-untyped-def]
        self,
        method: str | bytes,
        path: str,
        expected_code: int = 200,
        *,
        allow_redirect_to_login: bool = False,
        **kwargs,
    ) -> requests.Response:
        url = self.site.url_for_path(path)

        # May raise "requests.exceptions.ConnectionError: ('Connection aborted.', BadStatusLine("''",))"
        # suddenly without known reason. This may be related to some
        # apache or HTTP/1.1 issue when working with keepalive connections. See
        #   https://www.google.de/search?q=connection+aborted+Connection+aborted+bad+status+line
        #   https://github.com/mikem23/keepalive-race
        # Trying to workaround this by trying the problematic request a second time.
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.ConnectionError as e:
            if "Connection aborted" in "%s" % e:
                response = self.session.request(method, url, **kwargs)
            else:
                raise

        self._handle_http_response(response, expected_code, allow_redirect_to_login)
        return response

    def _handle_http_response(
        self, response: requests.Response, expected_code: int, allow_redirect_to_login: bool
    ) -> None:
        assert response.status_code == expected_code, (
            "Got invalid status code (%d != %d) for URL %s (Location: %s)"
            % (
                response.status_code,
                expected_code,
                response.url,
                response.headers.get("Location", "None"),
            )
        )

        if not allow_redirect_to_login and response.history:
            assert "check_mk/login.py" not in response.url, "Followed redirect (%d) %s -> %s" % (
                response.history[0].status_code,
                response.history[0].url,
                response.url,
            )

        if self._get_mime_type(response) == "text/html":
            soup = BeautifulSoup(response.text, "lxml")

            self._find_errors(response.text)
            self._check_html_page_resources(response.url, soup)

    def _get_mime_type(self, response: requests.Response) -> str:
        assert "Content-Type" in response.headers
        return response.headers["Content-Type"].split(";", 1)[0]

    def _find_errors(self, body: str) -> None:
        matches = re.search("<div class=error>(.*?)</div>", body, re.M | re.DOTALL)
        assert not matches, "Found error message: %s" % matches.groups()

    def _check_html_page_resources(self, url: str | bytes | None, soup: BeautifulSoup) -> None:
        base_url = urllib.parse.urlparse(url).path
        if ".py" in base_url:
            base_url = os.path.dirname(base_url)

        # There might be other resources like iframe, audio, ... but we don't care about them
        self._check_resources(soup, base_url, "img", "src", ["image/png", "image/svg+xml"])
        # The CSE includes a new onboarding feature. This is loaded from an external source hosted
        # by checkmk. We do not want to check it in the integration tests
        script_filters = (
            [("src", "https://static.saas-dev.cloudsandbox.checkmk.cloud")]
            if version_from_env().is_saas_edition()
            else None
        )
        self._check_resources(
            soup,
            base_url,
            "script",
            "src",
            ["application/javascript", "text/javascript"],
            filters=script_filters,
        )
        self._check_resources(
            soup, base_url, "link", "href", ["text/css"], filters=[("rel", "stylesheet")]
        )
        self._check_resources(
            soup,
            base_url,
            "link",
            "href",
            ["image/vnd.microsoft.icon"],
            filters=[("rel", "shortcut icon")],
        )

    def _check_resources(
        self,
        soup: BeautifulSoup,
        base_url: str | bytes,
        tag: str,
        attr: str,
        allowed_mime_types: Container,
        filters: Collection | None = None,
    ) -> None:
        for url in self._find_resource_urls(tag, attr, soup, filters):
            # Only check resources once per session
            if url in self.verified_resources:
                continue
            self.verified_resources.add(url)

            assert not url.startswith("/")
            assert isinstance(base_url, str)
            req = self.get(base_url + "/" + url, verify=False)

            mime_type = self._get_mime_type(req)
            assert mime_type in allowed_mime_types

    def _find_resource_urls(
        self, tag: str, attribute: str, soup: BeautifulSoup, filters: Collection | None = None
    ) -> list:
        urls = []

        for element in soup.findAll(tag):
            try:
                skip = False
                for attr, val in filters or []:
                    if element[attr] != val:
                        skip = True
                        break

                if not skip:
                    urls.append(element[attribute])
            except KeyError:
                pass

        return urls

    def login(
        self,
        username: str = "cmkadmin",
        password: str = "cmk",
    ) -> None:
        r = self.get("", allow_redirect_to_login=True)

        login_page_patterns = ("_username", "_password", "_login")
        main_page_patterns = ("sidebar", "dashboard.py")
        logged_in = all(_ in r.text for _ in main_page_patterns) and not any(
            _ in r.text for _ in login_page_patterns
        )

        assert not logged_in, "Logged in unexpectedly!"

        login_page = r.text
        for pattern in login_page_patterns:
            assert pattern in login_page, f"{pattern} not found in login page - page broken?"

        r = self.post(
            "login.py",
            data={
                "filled_in": "login",
                "_username": username,
                "_password": password,
                "_login": "Login",
            },
        )
        auth_cookie = self.session.cookies.get(f"auth_{self.site.id}")
        assert auth_cookie
        assert auth_cookie.startswith("%s:" % username)

        main_page = r.text
        for pattern in main_page_patterns:
            assert pattern in main_page, f"{pattern} not found in main page - page broken?"

    def logout(self) -> None:
        r = self.get("logout.py", allow_redirect_to_login=True)
        assert 'action="login.py"' in r.text

    def is_logged_in(self) -> bool:
        r = self.get("info.py", allow_redirect_to_login=True)
        return all(x in r.text for x in ("About Checkmk", "Your IT monitoring platform"))

    def get_auth_cookie(self) -> Cookie | None:
        """return the auth cookie

        apparently the get on these cookies return a str with only some information, also this is
        untyped and mypy would need some suppressions.
        We usually get two cookies so this for loop should not hurt too much"""

        for cookie in self.session.cookies:
            if cookie.name == f"auth_{self.site.id}":
                return cookie
        return None
