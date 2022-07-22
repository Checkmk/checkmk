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

import requests
from bs4 import BeautifulSoup  # type: ignore[import]


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

    def check_redirect(self, path, expected_target=None):
        response = self.get(path, expected_code=302, allow_redirects=False)
        if expected_target:
            if response.headers["Location"] != expected_target:
                raise AssertionError(
                    "REDIRECT FAILED: '%s' != '%s'"
                    % (response.headers["Location"], expected_target)
                )
            assert response.headers["Location"] == expected_target

    def get(self, *args, **kwargs):
        return self.request("get", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request("post", *args, **kwargs)

    def request(
        self,
        method,
        path,
        expected_code=200,
        add_transid=False,
        allow_redirect_to_login=False,
        **kwargs,
    ):
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

    def _add_transid(self, url):
        if not self.transids:
            raise Exception("Tried to add a transid, but none available at the moment")
        return url + ("&" if "?" in url else "?") + "_transid=" + self.transids.pop()

    def _handle_http_response(self, response, expected_code, allow_redirect_to_login):
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

    def _get_mime_type(self, response):
        assert "Content-Type" in response.headers
        return response.headers["Content-Type"].split(";", 1)[0]

    def _extract_transids(self, body, soup):
        """Extract transids from pages used in later actions issued by tests."""

        transids = set()

        # Extract from form hidden fields
        for element in soup.findAll(attrs={"name": "_transid"}):
            transids.add(element["value"])

        # Extract from URLs in the body
        transids.update(re.findall("_transid=([0-9/]+)", body))

        return list(transids)

    def _find_errors(self, body):
        matches = re.search("<div class=error>(.*?)</div>", body, re.M | re.DOTALL)
        assert not matches, "Found error message: %s" % matches.groups()

    def _check_html_page_resources(self, url, soup):
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

    def _check_resources(self, soup, base_url, tag, attr, allowed_mime_types, filters=None):
        for url in self._find_resource_urls(tag, attr, soup, filters):
            # Only check resources once per session
            if url in self.verified_resources:
                continue
            self.verified_resources.add(url)

            assert not url.startswith("/")
            req = self.get(base_url + "/" + url, verify=False)

            mime_type = self._get_mime_type(req)
            assert mime_type in allowed_mime_types

    def _find_resource_urls(self, tag, attribute, soup, filters=None):
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

    def login(self, username="cmkadmin", password="cmk"):
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

    def enforce_non_localized_gui(self):
        all_users = self.get_all_users()
        all_users["cmkadmin"]["language"] = "en"
        self.edit_htpasswd_users(all_users)

        # Verify the language is as expected now
        r = self.get("user_profile.py")
        assert "Edit profile" in r.text, "Body: %s" % r.text

    def logout(self):
        r = self.get("logout.py", allow_redirect_to_login=True)
        assert 'action="login.py"' in r.text

    #
    # Web-API for managing hosts, services etc.
    #

    def _automation_credentials(self):
        return {
            "_username": "automation",
            "_secret": self.site.get_automation_secret(),
        }

    def _api_request(self, url, data, expect_error=False, output_format="json"):
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

    def set_ruleset(self, ruleset_name, ruleset_spec):
        from cmk.utils.python_printer import pformat  # pylint: disable=import-outside-toplevel

        request = {
            "ruleset_name": ruleset_name,
        }
        request.update(ruleset_spec)

        result = self._api_request(
            "webapi.py?action=set_ruleset&output_format=python&request_format=python",
            {
                "request": pformat(request),
            },
            output_format="python",
        )

        assert result is None

    # TODO: Cleanup remaining API call
    def set_site(self, site_id, site_config):
        from cmk.utils.python_printer import pformat  # pylint: disable=import-outside-toplevel

        result = self._api_request(
            "webapi.py?action=set_site&request_format=python&output_format=python",
            {"request": pformat({"site_id": site_id, "site_config": site_config})},
            output_format="python",
        )
        assert result is None

    # TODO: Cleanup remaining API call
    def login_site(self, site_id, user="cmkadmin", password="cmk"):
        result = self._api_request(
            "webapi.py?action=login_site",
            {"request": json.dumps({"site_id": site_id, "username": user, "password": password})},
        )
        assert result is None

    # TODO: Cleanup remaining API call
    def get_all_users(self):
        return self._api_request("webapi.py?action=get_all_users", {})

    # TODO: Cleanup remaining API call
    def edit_htpasswd_users(self, users):
        result = self._api_request(
            "webapi.py?action=edit_users", {"request": json.dumps({"users": users})}
        )

        assert result is None
