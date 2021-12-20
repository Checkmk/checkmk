#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import logging
import os
import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup  # type: ignore[import]


class APIError(Exception):
    pass


logger = logging.getLogger()


class CMKWebSession:
    def __init__(self, site):
        super().__init__()
        self.transids = []
        # Resources are only fetched and verified once per session
        self.verified_resources = set()
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
        auth_cookie = r.cookies.get("auth_%s" % self.site.id)
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

    def add_host(
        self,
        hostname,
        folder="",
        attributes=None,
        cluster_nodes=None,
        create_folders=True,
        expect_error=False,
        verify_set_attributes=True,
    ):
        if attributes is None:
            attributes = {}

        result = self._api_request(
            "webapi.py?action=add_host",
            {
                "request": json.dumps(
                    {
                        "hostname": hostname,
                        "folder": folder,
                        "attributes": attributes or {},
                        "create_folders": create_folders,
                        "nodes": cluster_nodes,
                    }
                ),
            },
            expect_error=expect_error,
        )

        assert result is None

        if verify_set_attributes:
            host = self.get_host(hostname)

            assert host["hostname"] == hostname
            assert host["path"] == folder

            # Ignore the automatically generated meta_data attribute for the moment
            del host["attributes"]["meta_data"]

            assert host["attributes"] == attributes

    # hosts: List of tuples of this structure: (hostname, folder_path, attributes)
    def add_hosts(self, create_hosts):
        hosts = [
            {
                "hostname": hostname,
                "folder": folder,
                "attributes": attributes,
                "create_folders": True,
            }
            for hostname, folder, attributes in create_hosts
        ]

        result = self._api_request(
            "webapi.py?action=add_hosts",
            {
                "request": json.dumps(
                    {
                        "hosts": hosts,
                    }
                ),
            },
        )

        assert isinstance(result, dict)
        assert result["succeeded_hosts"] == [h["hostname"] for h in hosts]
        assert result["failed_hosts"] == {}
        hosts = self.get_all_hosts()
        for hostname, _folder, _attributes in create_hosts:
            assert hostname in hosts

    def edit_host(self, hostname, attributes=None, unset_attributes=None, cluster_nodes=None):
        if attributes is None:
            attributes = {}

        if unset_attributes is None:
            unset_attributes = []

        result = self._api_request(
            "webapi.py?action=edit_host",
            {
                "request": json.dumps(
                    {
                        "hostname": hostname,
                        "unset_attributes": unset_attributes,
                        "attributes": attributes,
                        "nodes": cluster_nodes,
                    }
                ),
            },
        )

        assert result is None

        host = self.get_host(hostname)

        assert host["hostname"] == hostname

        # Ignore the automatically generated meta_data attribute for the moment
        del host["attributes"]["meta_data"]

        assert host["attributes"] == attributes

    def edit_hosts(self, edit_hosts):
        hosts = [
            {
                "hostname": hostname,
                "attributes": attributes,
                "unset_attributes": unset_attributes,
            }
            for hostname, attributes, unset_attributes in edit_hosts
        ]

        result = self._api_request(
            "webapi.py?action=edit_hosts",
            {
                "request": json.dumps(
                    {
                        "hosts": hosts,
                    }
                ),
            },
        )

        assert isinstance(result, dict)
        assert result["succeeded_hosts"] == [h["hostname"] for h in hosts]
        assert result["failed_hosts"] == {}

        hosts = self.get_all_hosts()
        for hostname, attributes, unset_attributes in edit_hosts:
            host = hosts[hostname]

            for k, v in attributes.items():
                assert host["attributes"][k] == v

            for unset in unset_attributes:
                assert unset not in host["attributes"]

    def get_host(self, hostname, effective_attributes=False):
        result = self._api_request(
            "webapi.py?action=get_host",
            {
                "request": json.dumps(
                    {
                        "hostname": hostname,
                        "effective_attributes": effective_attributes,
                    }
                ),
            },
        )

        assert isinstance(result, dict)
        assert "hostname" in result
        assert "path" in result
        assert "attributes" in result

        return result

    def get_ruleset(self, ruleset_name):
        result = self._api_request(
            "webapi.py?action=get_ruleset&output_format=python",
            {
                "request": json.dumps(
                    {
                        "ruleset_name": ruleset_name,
                    }
                ),
            },
            output_format="python",
        )

        assert isinstance(result, dict)
        assert "ruleset" in result
        assert "configuration_hash" in result

        return result

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

    def get_hosttags(self):
        result = self._api_request(
            "webapi.py?action=get_hosttags&output_format=python",
            {
                "request": json.dumps({}),
            },
            output_format="python",
        )

        assert isinstance(result, dict)
        assert "aux_tags" in result
        assert "tag_groups" in result
        return result

    def set_hosttags(self, request):
        result = self._api_request(
            "webapi.py?action=set_hosttags&output_format=python",
            {
                "request": json.dumps(request),
            },
            output_format="python",
        )

        assert result is None

    def get_all_hosts(self, effective_attributes=False):
        result = self._api_request(
            "webapi.py?action=get_all_hosts",
            {
                "request": json.dumps(
                    {
                        "effective_attributes": effective_attributes,
                    }
                ),
            },
        )

        assert isinstance(result, dict)
        return result

    def delete_host(self, hostname):
        result = self._api_request(
            "webapi.py?action=delete_host",
            {
                "request": json.dumps(
                    {
                        "hostname": hostname,
                    }
                ),
            },
        )

        assert result is None

        hosts = self.get_all_hosts()
        assert hostname not in hosts

    def delete_hosts(self, hostnames):
        result = self._api_request(
            "webapi.py?action=delete_hosts",
            {
                "request": json.dumps(
                    {
                        "hostnames": hostnames,
                    }
                ),
            },
        )

        assert result is None

        hosts = self.get_all_hosts()
        for hostname in hostnames:
            assert hostname not in hosts

    def get_all_groups(self, group_type):
        result = self._api_request("webapi.py?action=get_all_%sgroups" % group_type, {})
        return result

    def set_site(self, site_id, site_config):
        from cmk.utils.python_printer import pformat  # pylint: disable=import-outside-toplevel

        result = self._api_request(
            "webapi.py?action=set_site&request_format=python&output_format=python",
            {"request": pformat({"site_id": site_id, "site_config": site_config})},
            output_format="python",
        )
        assert result is None

    def get_site(self, site_id):
        result = self._api_request(
            "webapi.py?action=get_site&request_format=python&output_format=python",
            {"request": json.dumps({"site_id": site_id})},
            output_format="python",
        )

        assert result is not None
        return result

    def get_all_sites(self):
        result = self._api_request(
            "webapi.py?action=get_all_sites&output_format=python", {}, output_format="python"
        )
        assert result is not None
        return result

    def delete_site(self, site_id):
        result = self._api_request(
            "webapi.py?action=delete_site&output_format=python",
            {"request": json.dumps({"site_id": site_id})},
            output_format="python",
        )

        assert result is None

    def set_all_sites(self, configuration):
        from cmk.utils.python_printer import pformat  # pylint: disable=import-outside-toplevel

        result = self._api_request(
            "webapi.py?action=set_all_sites&request_format=python",
            {"request": pformat(configuration)},
        )

        assert result is None

    def login_site(self, site_id, user="cmkadmin", password="cmk"):
        result = self._api_request(
            "webapi.py?action=login_site",
            {"request": json.dumps({"site_id": site_id, "username": user, "password": password})},
        )
        assert result is None

    def add_group(self, group_type, group_name, attributes, expect_error=False):
        request_object = {"groupname": group_name}
        request_object.update(attributes)

        result = self._api_request(
            "webapi.py?action=add_%sgroup" % group_type,
            {"request": json.dumps(request_object)},
            expect_error=expect_error,
        )

        assert result is None

    def edit_group(self, group_type, group_name, attributes, expect_error=False):
        request_object = {"groupname": group_name}
        request_object.update(attributes)

        result = self._api_request(
            "webapi.py?action=edit_%sgroup" % group_type,
            {"request": json.dumps(request_object)},
            expect_error=expect_error,
        )

        assert result is None

    def delete_group(self, group_type, group_name, expect_error=False):
        result = self._api_request(
            "webapi.py?action=delete_%sgroup" % group_type,
            {
                "request": json.dumps(
                    {
                        "groupname": group_name,
                    }
                )
            },
            expect_error=expect_error,
        )

        assert result is None

    def get_all_users(self):
        return self._api_request("webapi.py?action=get_all_users", {})

    def add_htpasswd_users(self, users):
        result = self._api_request(
            "webapi.py?action=add_users", {"request": json.dumps({"users": users})}
        )
        assert result is None

    def edit_htpasswd_users(self, users):
        result = self._api_request(
            "webapi.py?action=edit_users", {"request": json.dumps({"users": users})}
        )

        assert result is None

    def delete_htpasswd_users(self, userlist):
        result = self._api_request(
            "webapi.py?action=delete_users",
            {
                "request": json.dumps({"users": userlist}),
            },
        )
        assert result is None

    def discover_services(self, hostname, mode=None):
        request = {
            "hostname": hostname,
        }

        if mode is not None:
            request["mode"] = mode

        result = self._api_request(
            "webapi.py?action=discover_services",
            {
                "request": json.dumps(request),
            },
        )

        assert isinstance(result, str)
        assert result.startswith("Service discovery successful"), "Failed to discover: %r" % result

    def bulk_discovery_start(self, request, expect_error=False):
        result = self._api_request(
            "webapi.py?action=bulk_discovery_start",
            {
                "request": json.dumps(request),
            },
            expect_error=expect_error,
        )
        assert isinstance(result, dict)
        return result

    def bulk_discovery_status(self):
        result = self._api_request("webapi.py?action=bulk_discovery_status", {})
        assert isinstance(result, dict)
        return result

    def get_user_sites(self, expect_error=False):
        result = self._api_request(
            "webapi.py?action=get_user_sites",
            {
                "request": json.dumps({}),
            },
            expect_error=expect_error,
        )
        assert isinstance(result, list)
        return result

    def get_host_names(self, request, expect_error=False):
        result = self._api_request(
            "webapi.py?action=get_host_names",
            {
                "request": json.dumps(request),
            },
            expect_error=expect_error,
        )
        assert isinstance(result, list)
        return result

    def get_metrics_of_host(self, request, expect_error=False):
        result = self._api_request(
            "webapi.py?action=get_metrics_of_host",
            {
                "request": json.dumps(request),
            },
            expect_error=expect_error,
        )
        assert isinstance(result, dict)
        return result

    def get_graph_recipes(self, request, expect_error=False):
        result = self._api_request(
            "webapi.py?action=get_graph_recipes",
            {
                "request": json.dumps(request),
            },
            expect_error=expect_error,
        )
        assert isinstance(result, list)
        return result

    def get_combined_graph_identifications(self, request, expect_error=False):
        result = self._api_request(
            "webapi.py?action=get_combined_graph_identifications",
            {
                "request": json.dumps(request),
            },
            expect_error=expect_error,
        )
        assert isinstance(result, list)
        return result

    def get_graph_annotations(self, request, expect_error=False):
        result = self._api_request(
            "webapi.py?action=get_graph_annotations",
            {
                "request": json.dumps(request),
            },
            expect_error=expect_error,
        )
        assert isinstance(result, dict)
        return result

    def get_regular_graph(self, hostname, service_description, graph_index, expect_error=False):
        result = self._api_request(
            "webapi.py?action=get_graph&output_format=json",
            {
                "request": json.dumps(
                    {
                        "specification": [
                            "template",
                            {
                                "service_description": service_description,
                                "site": self.site.id,
                                "graph_index": graph_index,
                                "host_name": hostname,
                            },
                        ],
                        "data_range": {"time_range": [time.time() - 3600, time.time()]},
                    }
                ),
            },
            expect_error=expect_error,
            output_format="json",
        )

        assert isinstance(result, dict)
        assert "start_time" in result
        assert isinstance(result["start_time"], int)
        assert "end_time" in result
        assert isinstance(result["end_time"], int)
        assert "step" in result
        assert isinstance(result["step"], int)
        assert "curves" in result
        assert isinstance(result["curves"], list)
        assert len(result["curves"]) > 0

        for curve in result["curves"]:
            assert "color" in curve
            assert "rrddata" in curve
            assert "line_type" in curve
            assert "title" in curve

        return result

    def get_inventory(self, hosts, site=None, paths=None):
        request = {
            "hosts": hosts,
        }
        if site is not None:
            request["site"] = site
        if paths is not None:
            request["paths"] = paths
        result = self._api_request(
            "webapi.py?action=get_inventory",
            {
                "request": json.dumps(request),
            },
        )

        assert isinstance(result, dict)
        for host in hosts:
            assert isinstance(result[host], dict)
        return result
