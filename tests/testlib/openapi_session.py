#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, AnyStr, NamedTuple

import requests

from tests.testlib.rest_api_client import RequestHandler, Response
from tests.testlib.version import CMKVersion

from cmk.gui.http import HTTPMethod

logger = logging.getLogger("rest-session")


class RequestSessionRequestHandler(RequestHandler):
    def __init__(self) -> None:
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
            allow_redirects=True,
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
        self.status_code = status_code


class NoActiveChanges(RestSessionException):
    pass


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
        site_version: CMKVersion,
        port: int = 80,
        site: str = "heute",
        api_version: str = "1.0",
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.site = site
        self.site_version = site_version
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

        if response.status_code != 204:
            if (content_type := response.headers.get("content-type")) in (
                "application/json",
                "application/json; charset=utf-8",
                "text/html; charset=utf-8",
                "application/problem+json",
            ):
                logger.debug("< [%s] %s", response.status_code, response.text)
            else:
                logger.debug(
                    "< [%s] Unhandled content type %r (length: %d)",
                    response.status_code,
                    content_type,
                    len(response.content),
                )

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
    ) -> None:
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
            return  # changes are activated
        if response.status_code == 422:
            raise NoActiveChanges  # there are no changes
        if 300 <= response.status_code < 400:
            raise Redirect(redirect_url=response.headers["Location"])  # activation pending
        raise UnexpectedResponse.from_response(response)

    def pending_changes(self, sites: list[str] | None = None) -> list[dict[str, Any]]:
        """Returns a list of all changes currently pending."""
        response = self.get("/domain-types/activation_run/collections/pending_changes")
        assert response.status_code == 200
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def activate_changes_and_wait_for_completion(
        self,
        sites: list[str] | None = None,
        force_foreign_changes: bool = False,
        timeout: int = 300,
    ) -> bool:
        """Activate changes via REST API and wait for completion.

        Returns:
            * True if changes are activated
            * False if there are no changes to be activated
        """
        logger.info("Activate changes and wait %ds for completion...", timeout)
        with self._wait_for_completion(timeout, "get", "activate_changes"):
            try:
                self.activate_changes(sites, force_foreign_changes)
            except NoActiveChanges:
                return False

        pending_changes = self.pending_changes()
        assert (
            not pending_changes
        ), f"There are pending changes that were not activated: {pending_changes}"

        return True

    def create_user(
        self,
        username: str,
        fullname: str,
        password: str,
        email: str,
        contactgroups: list[str],
        customer: None | str = None,
        roles: list[str] | None = None,
    ) -> None:
        body = {
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
            "roles": roles or [],
        }
        if customer:
            body["customer"] = customer
        response = self.post(
            "domain-types/user_config/collections/all",
            json=body,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def get_all_users(self) -> list[User]:
        response = self.get("domain-types/user_config/collections/all")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return [User(title=user_dict["title"]) for user_dict in response.json()["value"]]

    def get_user(self, username: str) -> tuple[dict[Any, str], str] | None:
        """
        Returns
            a tuple with the user details and the Etag header if the user was found
            None if the user was not found
        """
        response = self.get(f"/objects/user_config/{username}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

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
        title: str | None = None,
        attributes: Mapping[str, Any] | None = None,
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

    def get_folder(self, folder: str) -> tuple[dict[Any, str], str] | None:
        """
        Returns
            a tuple with the folder details and the Etag header if the folder was found
            None if the folder was not found
        """
        response = self.get(f"/objects/folder_config/{folder.replace('/', '~')}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def create_host(
        self,
        hostname: str,
        folder: str = "/",
        attributes: Mapping[str, Any] | None = None,
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

    def bulk_create_hosts(
        self,
        entries: list[dict[str, Any]],
        bake_agent: bool = False,
        ignore_existing: bool = False,
    ) -> list[dict[str, Any]]:
        if ignore_existing:
            existing_hosts = [_.get("id") for _ in self.get_hosts()]
            entries = [_ for _ in entries if _.get("host_name") not in existing_hosts]
        query_string = "?bake_agent=1" if bake_agent else ""
        response = self.post(
            f"/domain-types/host_config/actions/bulk-create/invoke{query_string}",
            json={"entries": entries},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()
        return value

    def get_host(self, hostname: str) -> tuple[dict[Any, str], str] | None:
        """
        Returns
            a tuple with the host details and the Etag header if the host was found
            None if the host was not found
        """
        response = self.get(f"/objects/host_config/{hostname}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def get_hosts(self) -> list[dict[str, Any]]:
        response = self.get(
            "/domain-types/host_config/collections/all", params={"include_links": False}
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def delete_host(self, hostname: str) -> None:
        response = self.delete(f"/objects/host_config/{hostname}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def bulk_delete_hosts(self, hostnames: list[str]) -> None:
        response = self.post(
            "/domain-types/host_config/actions/bulk-delete/invoke",
            json={"entries": hostnames},
        )
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
        if 300 <= response.status_code < 400:
            # rename pending
            raise Redirect(redirect_url=response.headers["Location"])
        if not response.status_code == 200:
            raise UnexpectedResponse.from_response(response)

    def rename_host_and_wait_for_completion(
        self,
        *,
        hostname_old: str,
        hostname_new: str,
        etag: str,
        timeout: int = 120,
    ) -> None:
        logger.info(
            "Rename host %s to %s and wait %ds for completion...",
            hostname_old,
            hostname_new,
            timeout,
        )
        with self._wait_for_completion(timeout, "get", "rename_host"):
            self.rename_host(hostname_old=hostname_old, hostname_new=hostname_new, etag=etag)
            assert (
                self.get_host(hostname_new) is not None
            ), 'Failed to rename host "{hostname_old}" to "{hostname_new}"!'

    def create_host_group(self, name: str, alias: str) -> requests.Response:
        response = self.post(
            "/domain-types/host_group_config/collections/all",
            json={"name": name, "alias": alias},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def get_host_group(self, name: str) -> tuple[dict[Any, str], str]:
        response = self.get(f"/objects/host_group_config/{name}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def delete_host_group(self, name: str) -> None:
        response = self.delete(f"/objects/host_group_config/{name}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def discover_services(
        self,
        hostname: str,
        mode: str = "tabula_rasa",
    ) -> None:
        response = self.post(
            "/domain-types/service_discovery_run/actions/start/invoke",
            json={
                "host_name": hostname,
                "mode": mode,
            },
            # We want to get the redirect response and handle that below. So don't let requests
            # handle that for us.
            allow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            raise Redirect(redirect_url=response.headers["Location"])  # activation pending
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def bulk_discover_services_and_wait_for_completion(
        self,
        hostnames: list[str],
        monitor_undecided_services: bool = True,
        remove_vanished_services: bool = False,
        update_service_labels: bool = False,
        update_host_labels: bool = True,
        do_full_scan: bool = True,
        bulk_size: int = 10,
        ignore_errors: bool = True,
    ) -> str:
        body = {
            "hostnames": hostnames,
            "do_full_scan": do_full_scan,
            "bulk_size": bulk_size,
            "ignore_errors": ignore_errors,
        }

        if self.site_version >= CMKVersion("2.3.0", self.site_version.edition):
            body["options"] = {
                "monitor_undecided_services": monitor_undecided_services,
                "remove_vanished_services": remove_vanished_services,
                "update_service_labels": update_service_labels,
                "update_host_labels": update_host_labels,
            }
        else:
            body["mode"] = "new"

        response = self.post(
            "/domain-types/discovery_run/actions/bulk-discovery-start/invoke", json=body
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        job_id: str = response.json()["id"]
        while self.get_bulk_discovery_status(job_id) in (
            "initialized",
            "running",
        ):
            time.sleep(0.5)

        status = self.get_bulk_discovery_job_status(job_id)

        if status["extensions"]["state"] != "finished":
            raise RuntimeError(f"Discovery job {job_id} failed: {status}")

        output = "\n".join(status["extensions"]["logs"]["progress"])
        if "Traceback (most recent call last)" in output:
            raise RuntimeError(f"Found traceback in job output: {output}")
        if "0 failed" not in output:
            raise RuntimeError(f"Found a failure in job output: {output}")

        return job_id

    def get_bulk_discovery_status(self, job_id: str) -> str:
        job_status_response = self.get_bulk_discovery_job_status(job_id)
        status: str = job_status_response["extensions"]["state"]
        return status

    def get_bulk_discovery_job_status(self, job_id: str) -> dict:
        response = self.get(f"/objects/discovery_run/{job_id}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        job_status_response: dict = response.json()
        return job_status_response

    def get_discovery_status(self, hostname: str) -> str:
        job_status_response = self.get_discovery_job_status(hostname)
        status: str = job_status_response["extensions"]["state"]
        return status

    def get_discovery_job_status(self, hostname: str) -> dict:
        response = self.get(f"/objects/service_discovery_run/{hostname}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        job_status_response: dict = response.json()
        return job_status_response

    def discover_services_and_wait_for_completion(
        self, hostname: str, mode: str = "tabula_rasa", timeout: int = 60
    ) -> None:
        with self._wait_for_completion(timeout, "get", "discover_services"):
            self.discover_services(hostname, mode)
            discovery_status = self.get_discovery_status(hostname)
            assert (
                discovery_status == "finished"
            ), f"Unexpected service discovery status: {discovery_status}"

    @contextmanager
    def _wait_for_completion(
        self,
        timeout: int,
        http_method_for_redirection: HTTPMethod,
        operation: str,
    ) -> Iterator[None]:
        start = time.time()
        try:
            yield None
        except Redirect as redirect:
            self._handle_wait_redirect(
                start,
                timeout,
                http_method_for_redirection,
                operation,
                redirect.redirect_url
                if redirect.redirect_url.startswith("http://")
                else f"http://{self.host}:{self.port}{redirect.redirect_url}",
            )
        else:
            logger.info("Wait for completion finished instantly for %s", operation)

    def _handle_wait_redirect(
        self,
        start: float,
        timeout: int,
        http_method_for_redirection: HTTPMethod,
        operation: str,
        redirect_url: str,
    ) -> None:
        response = None
        while redirect_url:
            if (running_time := time.time() - start) > timeout:
                msg = f"Wait for completion timed out after {running_time}s for {operation}; URL={redirect_url}!"
                if response and response.content:
                    msg += f"; Last response: {response.status_code}; {response.content}"
                raise TimeoutError(msg)
            logger.debug('Redirecting to "%s %s"...', http_method_for_redirection, redirect_url)
            response = self.request(
                method=http_method_for_redirection,
                url=redirect_url,
                allow_redirects=False,
            )
            if response.status_code == 204 and not response.content:
                logger.info(
                    "Wait for completion finished after %0.2fs for %s", running_time, operation
                )
                break

            if not 300 <= response.status_code < 400:
                raise UnexpectedResponse.from_response(response)

            time.sleep(0.5)

    def get_host_services(
        self, hostname: str, pending: bool | None = None, columns: list[str] | None = None
    ) -> list[dict[str, Any]]:
        if pending is not None:
            if columns is None:
                columns = ["has_been_checked"]
            elif "has_been_checked" not in columns:
                columns.append("has_been_checked")
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
        value: object,
        ruleset_name: str | None = None,
        folder: str = "/",
        conditions: dict[str, Any] | None = None,
    ) -> str:
        response = self.post(
            "/domain-types/rule/collections/all",
            json=(
                {
                    "ruleset": ruleset_name,
                    "folder": folder,
                    "properties": {
                        "disabled": False,
                    },
                    "value_raw": repr(value),
                    "conditions": conditions or {},
                }
                if ruleset_name
                else value
            ),
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        the_id: str = response.json()["id"]
        return the_id

    def get_rule(self, rule_id: str) -> tuple[dict[Any, str], str] | None:
        """
        Returns
            a tuple with the rule details and the Etag header if the rule_id was found
            None if the rule_id was not found
        """
        response = self.get(f"/objects/rule/{rule_id}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

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

    def get_rulesets(self) -> list[dict[str, Any]]:
        response = self.get(
            "/domain-types/ruleset/collections/all",
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

    def update_site(self, site_id: str, site_config: dict) -> None:
        response = self.put(
            f"/objects/site_connection/{site_id}",
            headers={
                "Content-Type": "application/json",
            },
            json={"site_config": site_config},
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def show_site(self, site_id: str) -> dict[str, Any]:
        response = self.get(
            f"/objects/site_connection/{site_id}",
            headers={
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        value: dict[str, Any] = response.json()
        return value

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

    def create_dynamic_host_configuration(
        self,
        dcd_id: str,
        title: str,
        comment: str = "",
        disabled: bool = False,
        restrict_source_hosts: list | None = None,
        interval: int = 60,
        host_attributes: dict | None = None,
        delete_hosts: bool = False,
        discover_on_creation: bool = True,
        no_deletion_time_after_init: int = 600,
        max_cache_age: int = 3600,
        validity_period: int = 60,
    ) -> None:
        """Create a DCD connection via REST API."""
        resp = self.post(
            "/domain-types/dcd/collections/all",
            json={
                "dcd_id": dcd_id,
                "title": title,
                "comment": comment,
                "disabled": disabled,
                "site": self.site,
                "connector_type": "piggyback",
                "restrict_source_hosts": restrict_source_hosts or [],
                "interval": interval,
                "creation_rules": [
                    {
                        "folder_path": "/",
                        "host_attributes": host_attributes or {},
                        "delete_hosts": delete_hosts,
                    }
                ],
                "discover_on_creation": discover_on_creation,
                "no_deletion_time_after_init": no_deletion_time_after_init,
                "max_cache_age": max_cache_age,
                "validity_period": validity_period,
            },
        )
        if resp.status_code != 200:
            raise UnexpectedResponse.from_response(resp)

    def delete_dynamic_host_configuration(self, dcd_id: str) -> None:
        """Delete a DCD connection via REST API."""
        resp = self.delete(f"/objects/dcd/{dcd_id}")
        if resp.status_code != 204:
            raise UnexpectedResponse.from_response(resp)

    def create_ldap_connection(
        self,
        ldap_id: str,
        user_base_dn: str,
        user_search_filter: str | None,
        user_id_attribute: str | None,
        group_base_dn: str,
        group_search_filter: str | None,
        ldap_server: str,
        bind_dn: str,
        password: str,
    ) -> None:
        """Create an LDAP connection via REST API."""
        users = {
            "user_base_dn": user_base_dn,
            "search_scope": "search_whole_subtree",
            "search_filter": {
                "state": "disabled",
            },
            "filter_group": {"state": "disabled"},
            "user_id_attribute": {
                "state": "disabled",
            },
            "user_id_case": "dont_convert_to_lowercase",
            "umlauts_in_user_ids": "keep_umlauts",
            "create_users": "on_sync",
        }
        if user_search_filter:
            users["search_filter"] = {
                "state": "enabled",
                "filter": user_search_filter,
            }
        if user_id_attribute:
            users["user_id_attribute"] = {
                "state": "enabled",
                "attribute": user_id_attribute,
            }

        groups = {
            "group_base_dn": group_base_dn,
            "search_scope": "search_whole_subtree",
            "search_filter": {
                "state": "disabled",
            },
            "member_attribute": {
                "state": "disabled",
            },
        }
        if group_search_filter:
            groups["search_filter"] = {
                "state": "enabled",
                "filter": group_search_filter,
            }

        resp = self.post(
            "/domain-types/ldap_connection/collections/all",
            json={
                "users": users,
                "groups": groups,
                "sync_plugins": {},
                "other": {
                    "sync_interval": {
                        "days": 0,
                        "hours": 0,
                        "minutes": 1,
                    },
                },
                "general_properties": {
                    "id": ldap_id,
                    "description": "test ldap connection",
                    "comment": "",
                    "documentation_url": "",
                    "rule_activation": "activated",
                },
                "ldap_connection": {
                    "directory_type": {
                        "type": "active_directory_manual",
                        "ldap_server": ldap_server,
                    },
                    "bind_credentials": {
                        "state": "enabled",
                        "type": "explicit",
                        "bind_dn": bind_dn,
                        "explicit_password": password,
                    },
                    "tcp_port": {
                        "state": "disabled",
                    },
                    "ssl_encryption": "disable_ssl",
                    "connect_timeout": {
                        "state": "disabled",
                    },
                    "ldap_version": {
                        "state": "disabled",
                    },
                    "page_size": {
                        "state": "disabled",
                    },
                    "response_timeout": {
                        "state": "disabled",
                    },
                    "connection_suffix": {
                        "state": "disabled",
                    },
                },
            },
        )
        if resp.status_code != 200:
            raise UnexpectedResponse.from_response(resp)

    def delete_ldap_connection(self, ldap_id: str) -> None:
        """Delete an LDAP connection via REST API."""
        resp = self.delete(f"/objects/ldap_connection/{ldap_id}", headers={"If-Match": "*"})
        if resp.status_code != 204:
            raise UnexpectedResponse.from_response(resp)

    def create_password(
        self,
        ident: str,
        title: str,
        comment: str,
        password: str,
        owner: str = "admin",
    ) -> None:
        """Create a password via REST API."""
        response = self.post(
            "/domain-types/password/collections/all",
            json={
                "ident": ident,
                "title": title,
                "comment": comment,
                "documentation_url": "localhost",
                "password": password,
                "owner": owner,
                "shared": ["all"],
            },
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
