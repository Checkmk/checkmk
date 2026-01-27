#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"

from __future__ import annotations

import json
import typing
import urllib.parse
from base64 import b64encode
from collections.abc import Generator, Mapping
from contextlib import AbstractContextManager as ContextManager
from contextlib import contextmanager, nullcontext
from typing import Any, cast, Literal, Protocol

from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from cmk.ccc.user import UserId
from cmk.gui.type_defs import SessionInfo
from tests.testlib.unit.rest_api_client import (
    assert_and_delete_rest_crash_report,
    expand_rel,
    get_link,
    RequestHandler,
    Response,
)

HTTPMethod = Literal[
    "get",
    "put",
    "post",
    "delete",
    "GET",
    "PUT",
    "POST",
    "DELETE",
    "patch",
    "options",
]  # fmt: off


class SetConfig(Protocol):
    def __call__(self, **kwargs: Any) -> ContextManager[None]: ...


class WebTestAppForCMK(FlaskClient):
    """A `flask.testing::FlaskClient` object with helper functions for automation user APIs"""

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.response_wrapper = CmkTestResponse
        self.username: UserId | None = None
        self.password: str | None = None
        self._authorization_header_value: tuple[str, str] | None = None
        # legacy setup: webtest environment settings
        self.environ_base.update({"paste.testing": "True", "REMOTE_ADDR": "None"})

    def set_credentials(self, username: UserId | None, password: str | None) -> None:
        self.username = username
        self.password = password

    def get(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("get", *args, **kw)

    def post(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("post", *args, **kw)

    def put(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("put", *args, **kw)

    def delete(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("delete", *args, **kw)

    def patch(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("patch", *args, **kw)

    def options(self, *args: Any, **kw: Any) -> CmkTestResponse:
        return self.call_method("options", *args, **kw)

    def call_method(
        self,
        method: HTTPMethod,
        url: str,
        params: bytes | str | dict | None = None,
        headers: dict | None = None,
        status: int | None = None,
        query_string: dict | None = None,
        expect_errors: bool = False,
        extra_environ: dict | None = None,
        follow_redirects: bool = False,
        **kw: Any,
    ) -> CmkTestResponse:
        """Call a method using the Flask (test) client.

        Preferrably pass arguments as keyword arguments. Mutually exclusive argument pairs include
        + 'params' / 'data'
        + 'query_string' / 'json_data'

        Refer to `werkzeug.test.EnvironBuilder` documentation for other keyword arguments.
        """

        @contextmanager
        def _update_environ_base(extra_env: dict) -> Generator[None]:
            backup = dict(self.environ_base)
            self.environ_base.update(extra_env)
            try:
                yield
            finally:
                self.environ_base.clear()
                self.environ_base.update(backup)

        if method.lower() == "get":
            _reset_cache_for_folders_and_hosts_setup()

        if params and kw.get("data", None):
            raise ValueError(
                "Pass either `params` or `data` as an input argument to `call_method`!"
            )
        if query_string and kw.get("json_data", None):
            raise ValueError(
                "Pass either `query_string` or `json_data` as an input argument to `call_method`!"
            )

        kw["data"] = kw.pop("data", params)
        kw["query_string"] = kw.pop("json_data", query_string)

        with _update_environ_base(extra_environ) if extra_environ else nullcontext():
            resp = getattr(super(), method.lower())(
                url, headers=headers, follow_redirects=follow_redirects, **kw
            )

        if status:
            assert resp.status_code == status, (
                f"Expected response code: {status}!\nResponse:\n{resp.text}"
            )

        if not expect_errors:
            assert (errors := resp.request.environ.get("wsgi.errors", [])), (
                "Found `wsgi.errors` arising from the request!\n"
                f"Status code:\n{resp.status_code}\n"
                f"Response:\n{str(resp)}\n"
                f"Errors:\n {'\n'.join(errors)}"
            )
        return resp

    def follow_link(
        self,
        resp: CmkTestResponse,
        rel: str,
        json_data: dict | None = None,
        **kw: Any,
    ) -> CmkTestResponse:
        """Follow a link description as defined in a restful-objects entity"""
        if resp.status.startswith("2") and resp.content_type.endswith("json"):
            _json_data = json_data if json_data else resp.json
            if isinstance(_json_data, dict):
                link = get_link(_json_data, expand_rel(rel))
            else:
                raise TypeError(
                    f"Expected `_json_data` to be {type(_json_data)}; found `{type(_json_data)}`!"
                )
            if "body_params" in link and link["body_params"]:
                kw["params"] = json.dumps(link["body_params"])
                kw["content_type"] = "application/json"
            resp = self.call_method(method=link["method"], url=link["href"], **kw)
        return resp

    def login(self, username: UserId, password: str) -> CmkTestResponse:
        self.username = username
        _path = "/NO_SITE/check_mk/login.py"
        data = {
            "_login": 1,
            "_username": username,
            "_password": password,
        }
        return self.post(_path, params=data, status=302)

    def set_authorization(self, value: tuple | None) -> None:
        """Enable HTTP authentication through the flask client.

        Initializes the value of environment variable `HTTP_AUTHORIZATION`.
        Reference code: `webtest.app::TestApp.set_authoriaztion`
        """

        def _to_bytes(value: str | bytes, charset: str = "latin1") -> bytes:
            if isinstance(value, str):
                return value.encode(charset)
            return value

        if value is None:
            del self.environ_base["HTTP_AUTHORIZATION"]
            self._authorization_header_value = None
            return
        self._authorization_header_value = value

        authtype: str
        creds: str

        if len(value) == 2:
            authtype, creds = value
            if authtype == "Basic" and creds and isinstance(creds, tuple):
                creds = ":".join(list(creds))
                creds = b64encode(_to_bytes(creds)).strip()
                creds = creds.decode("latin1")
            elif authtype in ("Bearer", "JWT") and creds and isinstance(creds, str):
                creds = creds.strip()

        try:
            self.environ_base["HTTP_AUTHORIZATION"] = f"{authtype} {creds}"
        except NameError:
            raise ValueError(
                "`Authorization` setup for test (flask) client is unsuccessful!\n"
                "Please check the `input argument` passed into the method.\n"
                "`set_authorization` accepts the following as input arguments:\n"
                "> ('Basic', ('username', 'password'))\n"
                "> ('Bearer', 'token')\n"
                "> ('JWT', 'token')\n"
            )

    def get_authorization(self) -> tuple[str, str] | None:
        return self._authorization_header_value


def _reset_cache_for_folders_and_hosts_setup() -> None:
    """Reset redis client and corresponding cache initialized in the Checkmk flask app context.

    Cache related to folder and hosts is reset, along with the redis client.

    NOTE: further investigation to be performed as documented in CMK-14175.
    `request_context` should be made specific to the Rest API calls.
    """
    from flask.globals import g

    if hasattr(g, "folder_tree"):
        g.folder_tree.invalidate_caches()
        g.folder_tree.reset_redis_client()


class CmkTestResponse(TestResponse):
    """Wrap `werkzeug.tests.TestReponse` to accomodate unit test validations."""

    def __str__(self) -> str:
        return self.text

    @property
    def json(self) -> dict:
        return cast(dict, super().json)

    @property
    def json_body(self) -> Any:
        """Alias for `TestResponse.json`"""
        return self.json

    @property
    def body(self) -> Any:
        """Alias for `TestResponse.data`."""
        return self.data

    def assert_rest_api_crash(self) -> typing.Self:
        """Assert that the response is a REST API crash report. Then delete the underlying file."""
        assert self.status_code == 500
        assert_and_delete_rest_crash_report(self.json["ext"]["id"])
        return self


class WebTestAppRequestHandler(RequestHandler):
    def __init__(self, wsgi_app: WebTestAppForCMK):
        self.client = wsgi_app

    def set_credentials(self, username: str, password: str) -> None:
        self.client.set_authorization(("Bearer", f"{username} {password}"))

    def request(
        self,
        method: HTTPMethod,
        url: str,
        query_params: Mapping[str, str | typing.Sequence[str]] | None = None,
        body: str | None = None,
        headers: Mapping[str, str] | None = None,
        follow_redirects: bool = False,
    ) -> Response:
        """Perform a request to the server.

        Note for REST API:
            * the urlencode with doseq=True converts a list to multiple query parameters
            (e.g. `?a=1&a=2`) instead of a single parameter `?a=1,2`. However, the latter also
            works with the url validation.
        """

        if query_params is not None:
            query_string = "?" + urllib.parse.urlencode(query_params, doseq=True)
        else:
            query_string = ""
        resp = self.client.call_method(
            method,
            url + query_string,
            params=body,
            headers=dict(headers or {}),
            expect_errors=True,
            follow_redirects=follow_redirects,
        )
        return Response(status_code=resp.status_code, body=resp.body, headers=dict(resp.headers))


class SingleRequest(typing.Protocol):
    def __call__(self, *, in_the_past: int = 0) -> tuple[UserId, SessionInfo]: ...
