#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import logging
import os
import re
import urllib.parse
from collections.abc import Container, Iterable, Mapping
from typing import Any, Collection

import requests
from bs4 import BeautifulSoup  # type: ignore[import]

from cmk.utils.type_defs import RulesetName


class APIError(Exception):
    pass


logger = logging.getLogger()


class CMKWebSession:
    def __init__(self, site) -> None:  # type:ignore[no-untyped-def]
        super().__init__()
        self.transids: list = []
        # Resources are only fetched and verified once per session
        self.verified_resources: set = set()
        self.site = site
        self.session = requests.Session()

    def check_redirect(self, path: str, expected_target: str | None = None) -> None:
        response = self.get(path, expected_code=302, allow_redirects=False)
        if expected_target:
            if response.headers["Location"] != expected_target:
                raise AssertionError(
                    "REDIRECT FAILED: '%s' != '%s'"
                    % (response.headers["Location"], expected_target)
                )
            assert response.headers["Location"] == expected_target

    def get(self, *args, **kwargs) -> requests.Response:  # type:ignore[no-untyped-def]
        return self.request("get", *args, **kwargs)

    def post(self, *args, **kwargs) -> requests.Response:  # type:ignore[no-untyped-def]
        return self.request("post", *args, **kwargs)

    def request(  # type:ignore[no-untyped-def]
        self,
        method: str | bytes,
        path: str,
        expected_code: int = 200,
        add_transid: bool = False,
        allow_redirect_to_login: bool = False,
        **kwargs,
    ) -> requests.Response:
        url = self.site.url_for_path(path)
        if add_transid:
            url = self._add_transid(url)

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

    def _add_transid(self, url: str) -> str:
        if not self.transids:
            raise Exception("Tried to add a transid, but none available at the moment")
        return url + ("&" if "?" in url else "?") + "_transid=" + self.transids.pop()

    def _handle_http_response(
        self, response: requests.Response, expected_code: int, allow_redirect_to_login: bool
    ) -> None:
        assert (
            response.status_code == expected_code
        ), "Got invalid status code (%d != %d) for URL %s (Location: %s)" % (
            response.status_code,
            expected_code,
            response.url,
            response.headers.get("Location", "None"),
        )

        if not allow_redirect_to_login and response.history:
            assert "check_mk/login.py" not in response.url, "Followed redirect (%d) %s -> %s" % (
                response.history[0].status_code,
                response.history[0].url,
                response.url,
            )

        if self._get_mime_type(response) == "text/html":
            soup = BeautifulSoup(response.text, "lxml")

            self.transids += self._extract_transids(response.text, soup)
            self._find_errors(response.text)
            self._check_html_page_resources(response.url, soup)

    def _get_mime_type(self, response: requests.Response) -> str:
        assert "Content-Type" in response.headers
        return response.headers["Content-Type"].split(";", 1)[0]

    def _extract_transids(self, body: str, soup: BeautifulSoup) -> list:
        """Extract transids from pages used in later actions issued by tests."""

        transids = set()

        # Extract from form hidden fields
        for element in soup.findAll(attrs={"name": "_transid"}):
            transids.add(element["value"])

        # Extract from URLs in the body
        transids.update(re.findall("_transid=([0-9/]+)", body))

        return list(transids)

    def _find_errors(self, body: str) -> None:
        matches = re.search("<div class=error>(.*?)</div>", body, re.M | re.DOTALL)
        assert not matches, "Found error message: %s" % matches.groups()

    def _check_html_page_resources(self, url: str | bytes | None, soup: BeautifulSoup) -> None:
        base_url = urllib.parse.urlparse(url).path
        if ".py" in base_url:
            base_url = os.path.dirname(base_url)

        # There might be other resources like iframe, audio, ... but we don't care about them
        self._check_resources(soup, base_url, "img", "src", ["image/png", "image/svg+xml"])
        self._check_resources(
            soup, base_url, "script", "src", ["application/javascript", "text/javascript"]
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

    def _find_resource_urls(  # type:ignore[no-untyped-def]
        self, tag: str, attribute, soup: BeautifulSoup, filters: Collection | None = None
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

    def login(self, username: str = "cmkadmin", password: str = "cmk") -> None:
        login_page = self.get("", allow_redirect_to_login=True).text
        assert "_username" in login_page, "_username not found on login page - page broken?"
        assert "_password" in login_page
        assert "_login" in login_page

        r = self.post(
            "login.py",
            data={
                "filled_in": "login",
                "_username": username,
                "_password": password,
                "_login": "Login",
            },
        )
        auth_cookie = self.session.cookies.get("auth_%s" % self.site.id)
        assert auth_cookie
        assert auth_cookie.startswith("%s:" % username)

        assert "sidebar" in r.text
        assert "dashboard.py" in r.text

    def logout(self) -> None:
        r = self.get("logout.py", allow_redirect_to_login=True)
        assert 'action="login.py"' in r.text

    #
    # Web-API for managing hosts, services etc.
    #

    def _automation_credentials(self) -> dict[str, Any]:
        return {
            "_username": "automation",
            "_secret": self.site.get_automation_secret(),
        }

    def _api_request(
        self,
        url: object,
        data: dict[str, object],
        expect_error: bool = False,
        output_format: str = "json",
    ) -> Mapping[str, object]:
        data.update(self._automation_credentials())

        req = self.post(url, data=data)

        if output_format == "json":
            try:
                response = json.loads(req.text)
            except json.JSONDecodeError:
                raise APIError(f"invalid json: {req.text}")
        elif output_format == "python":
            response = ast.literal_eval(req.text)
        else:
            raise NotImplementedError()

        assert req.headers["access-control-allow-origin"] == "*"

        if not expect_error:
            assert response["result_code"] == 0, "An error occured: %r" % response
        else:
            raise APIError(response["result"])

        return response["result"]

    def set_ruleset(
        self,
        ruleset_name: RulesetName,
        ruleset_spec: Iterable[tuple[str, RulesetName]] | Mapping[str, RulesetName],
    ) -> None:
        request = {
            "ruleset_name": ruleset_name,
        }
        request.update(ruleset_spec)

        result = self._api_request(
            "webapi.py?action=set_ruleset&output_format=python&request_format=python",
            {
                "request": str(request),
            },
            output_format="python",
        )

        assert result is None
