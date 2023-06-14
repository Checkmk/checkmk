#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, AnyStr, NamedTuple, NoReturn, Optional

import requests

from tests.testlib.rest_api_client import RequestHandler, Response

from cmk.gui.http import HTTPMethod

logger = logging.getLogger("rest-session")


class RequestSessionRequestHandler(RequestHandler):
    def __init__(self):
        self.session = requests.session()

    def request(
        self,
        method: HTTPMethod,
        url: str,
        query_params: Mapping[str, str] | None = None,
        body: AnyStr | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        resp = self.session.request(
            method=method,
            url=url,
            params=query_params,
            data=body,
            headers=headers,
            allow_redirects=False,
        )
        return Response(status_code=resp.status_code, body=resp.text.encode(), headers=resp.headers)

    def set_credentials(self, username: str, password: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {username} {password}"


class RestSessionException(Exception):
    pass


class UnexpectedResponse(RestSessionException):
    @classmethod
    def from_response(cls, response: requests.Response) -> "UnexpectedResponse":
        return cls(status_code=response.status_code, response_text=response.text)

    def __init__(self, status_code: int, response_text: str) -> None:
        super().__init__(f"[{status_code}] {response_text}")


class AuthorizationFailed(RestSessionException):
    pass


class Redirect(RestSessionException):
    def __init__(self, redirect_url: str) -> None:
        super().__init__(redirect_url)
        self.redirect_url = redirect_url


class BakingStatus(NamedTuple):
    state: str
    started: float


class User(NamedTuple):
    title: str


class CMKOpenApiSession(requests.Session):
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        port: int = 80,
        site: str = "heute",
        api_version: str = "1.0",
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.site = site
        self.api_version = api_version
        self.headers["Accept"] = "application/json"
        self.set_authentication_header(user, password)

    def set_authentication_header(self, user: str, password: str) -> None:
        self.headers["Authorization"] = f"Bearer {user} {password}"

    def request(  # type: ignore[no-untyped-def]
        self, method: str | bytes, url: str | bytes, *args, **kwargs
    ) -> requests.Response:
        """
        Suggested method to use a base url with a requests.Session
        see https://github.com/psf/requests/issues/2554#issuecomment-109341010
        """
        assert isinstance(method, str)  # HACK
        assert isinstance(url, str)  # HACK

        if not url.startswith("http://"):
            url = f"http://{self.host}:{self.port}/{self.site}/check_mk/api/{self.api_version}/{url.strip('/')}"

        logger.debug("> [%s] %s (%s, %s)", method, url, args, kwargs)
        response = super().request(method, url, *args, **kwargs)
        logger.debug("< [%s] %s", response.status_code, response.text)

        if response.status_code == 401:
            assert isinstance(self.headers["Authorization"], str)  # HACK
            raise AuthorizationFailed(
                f"Authorization failed on site {self.site}",
                response.headers,
                response.text,
            )

        return response

    def activate_changes(
        self,
        sites: list[str] | None = None,
        force_foreign_changes: bool = False,
    ) -> bool:
        """
        Returns
            True if changes are activated
            False if there are no changes to be activated
        """
        response = self.post(
            "/domain-types/activation_run/actions/activate-changes/invoke",
            json={
                "redirect": True,
                "sites": sites or [],
                "force_foreign_changes": force_foreign_changes,
            },
            headers={"If-Match": "*"},
            # We want to get the redirect response and handle that below. So don't let requests
            # handle that for us.
            allow_redirects=False,
        )
        if response.status_code == 200:
            return True  # changes are activated
        if response.status_code == 422:
            return False  # no changes
        if response.status_code == 302:
            raise Redirect(redirect_url=response.headers["Location"])  # activation pending
        raise UnexpectedResponse.from_response(response)

    def activate_changes_and_wait_for_completion(
        self,
        sites: list[str] | None = None,
        force_foreign_changes: bool = False,
        timeout: int = 60,
    ) -> bool:
        with self._wait_for_completion(timeout, "get"):
            return self.activate_changes(sites, force_foreign_changes)

    def create_user(
        self, username: str, fullname: str, password: str, email: str, contactgroups: list[str]
    ) -> None:
        response = self.post(
            "domain-types/user_config/collections/all",
            json={
                "username": username,
                "fullname": fullname,
                "auth_option": {
                    "auth_type": "password",
                    "password": password,
                },
                "contact_options": {
                    "email": email,
                },
                "contactgroups": contactgroups,
            },
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def get_all_users(self) -> list[User]:
        response = self.get("domain-types/user_config/collections/all")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return [User(title=user_dict["title"]) for user_dict in response.json()["value"]]

    def get_user(self, username: str) -> tuple[dict[str, Any], str]:
        response = self.get(f"/objects/user_config/{username}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        return response.json()["extensions"], response.headers["Etag"]

    def edit_user(self, username: str, user_spec: Mapping[str, Any], etag: str) -> None:
        response = self.put(
            f"objects/user_config/{username}",
            headers={
                "If-Match": etag,
            },
            json=user_spec,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def delete_user(self, username: str) -> None:
        response = self.delete(f"/objects/user_config/{username}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def create_folder(
        self,
        folder: str,
        title: Optional[str] = None,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if folder.count("/") > 1:
            parent_folder, folder_name = folder.rsplit("/", 1)
        else:
            parent_folder = "/"
            folder_name = folder.replace("/", "")
        response = self.post(
            "/domain-types/folder_config/collections/all",
            json={
                "name": folder_name,
                "title": title if title else folder_name,
                "parent": parent_folder,
                "attributes": attributes if attributes else {},
            },
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def get_folder(self, folder: str) -> list[dict[str, Any]]:
        response = self.get(f"/objects/folder_config/{folder.replace('/', '~')}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response.json()

    def create_host(
        self,
        hostname: str,
        folder: str = "/",
        attributes: dict[str, Any] | None = None,
        bake_agent: bool = False,
    ) -> requests.Response:
        query_string = "?bake_agent=1" if bake_agent else ""
        response = self.post(
            f"/domain-types/host_config/collections/all{query_string}",
            json={"folder": folder, "host_name": hostname, "attributes": attributes or {}},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def get_host(self, hostname: str) -> list[dict[str, Any]]:
        response = self.get(f"/objects/host_config/{hostname}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response.json()

    def get_hosts(self) -> list[dict[str, Any]]:
        response = self.get("/domain-types/host_config/collections/all")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def delete_host(self, hostname: str) -> None:
        response = self.delete(f"/objects/host_config/{hostname}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def rename_host(self, *, hostname_old: str, hostname_new: str, etag: str) -> None:
        response = self.put(
            f"/objects/host_config/{hostname_old}/actions/rename/invoke",
            headers={
                "If-Match": etag,
                "Content-Type": "application/json",
            },
            json={"new_name": hostname_new},
            allow_redirects=False,
        )
        if response.status_code == 302:
            raise Redirect(redirect_url=response.headers["Location"])
        if not response.ok:
            raise UnexpectedResponse.from_response(response)

    def rename_host_and_wait_for_completion(
        self,
        *,
        hostname_old: str,
        hostname_new: str,
        etag: str,
        timeout: int = 60,
    ) -> None:
        with self._wait_for_completion(timeout, "post"):
            self.rename_host(hostname_old=hostname_old, hostname_new=hostname_new, etag=etag)

    def discover_services(self, hostname: str, mode: str = "tabula_rasa") -> NoReturn:
        response = self.post(
            "/domain-types/service_discovery_run/actions/start/invoke",
            json={"host_name": hostname, "mode": mode},
            # We want to get the redirect response and handle that below. So don't let requests
            # handle that for us.
            allow_redirects=False,
        )
        if response.status_code == 302:
            raise Redirect(redirect_url=response.headers["Location"])  # activation pending
        raise UnexpectedResponse.from_response(response)

    def discover_services_and_wait_for_completion(self, hostname: str) -> None:
        timeout = 60
        with self._wait_for_completion(timeout, "get"):
            self.discover_services(hostname)

    @contextmanager
    def _wait_for_completion(
        self,
        timeout: int,
        http_method_for_redirection: HTTPMethod,
    ) -> Iterator[None]:
        start = time.time()
        try:
            yield None
        except Redirect as redirect:
            redirect_url = redirect.redirect_url
            while redirect_url:
                if time.time() > (start + timeout):
                    raise TimeoutError("wait for completion timed out")

                response = self.request(
                    method=http_method_for_redirection,
                    url=redirect_url,
                    allow_redirects=False,
                )
                if response.status_code == 204:  # job has finished
                    break

                if response.status_code != 302:
                    raise UnexpectedResponse.from_response(response)

                time.sleep(0.5)

    def get_host_services(
        self, hostname: str, pending: Optional[bool] = None, columns: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        if pending is not None:
            if columns:
                columns.append("has_been_checked")
            else:
                columns = ["has_been_checked"]
        query_string = "?columns=" + "&columns=".join(columns) if columns else ""
        response = self.get(f"/objects/host/{hostname}/collections/services{query_string}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        if pending is not None:
            value = [
                _
                for _ in value
                if _.get("extensions", {}).get("has_been_checked") == int(not pending)
            ]
        return value

    def get_baking_status(self) -> BakingStatus:
        response = self.get("/domain-types/agent/actions/baking_status/invoke")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        result = response.json()["result"]["value"]
        return BakingStatus(
            state=result["state"],
            started=result["started"],
        )

    def sign_agents(self, key_id: int, passphrase: str) -> None:
        response = self.post(
            "/domain-types/agent/actions/sign/invoke",
            json={"key_id": key_id, "passphrase": passphrase},
        )
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def create_rule(
        self,
        ruleset_name: str,
        value: object,
        folder: str = "/",
        conditions: dict[str, Any] | None = None,
    ) -> str:
        response = self.post(
            "/domain-types/rule/collections/all",
            json={
                "ruleset": ruleset_name,
                "folder": folder,
                "properties": {
                    "disabled": False,
                },
                "value_raw": repr(value),
                "conditions": conditions or {},
            },
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        the_id: str = response.json()["id"]
        return the_id

    def delete_rule(self, rule_id: str) -> None:
        response = self.delete(f"/objects/rule/{rule_id}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def get_rules(self, ruleset_name: str) -> list[dict[str, Any]]:
        response = self.get(
            "/domain-types/rule/collections/all",
            params={"ruleset_name": ruleset_name},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def create_site(self, site_config: dict) -> None:
        response = self.post(
            "/domain-types/site_connection/collections/all",
            headers={
                "Content-Type": "application/json",
            },
            json={"site_config": site_config},
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def login_to_site(self, site_id: str, user: str = "cmkadmin", password: str = "cmk") -> None:
        response = self.post(
            f"/objects/site_connection/{site_id}/actions/login/invoke",
            headers={
                "Content-Type": "application/json",
            },
            json={"username": user, "password": password},
        )

        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)
