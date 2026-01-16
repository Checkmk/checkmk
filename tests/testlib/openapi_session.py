#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Module Summary:
    This module implements a REST API client for interacting with the Checkmk system in tests.
    It extends the requests.Session class to provide custom URL construction, authentication,
    logging, and error handling tailored to the Checkmk API.

selected objects:
    - CMKOpenApiSession: A custom session class that manages HTTP requests and responses for
        Checkmk APIs. It automatically constructs request URLs, sets up authentication, logs
        request/response details, and handles HTTP redirection.
    - Exception Classes: Custom exceptions (e.g., RestSessionException, UnexpectedResponse,
        AuthorizationFailed, NoActiveChanges, Redirect) are defined to handle various error
        conditions encountered during API interactions.
    - API Interfaces: Multiple helper classes
        (e.g., ChangesAPI, UsersAPI, FoldersAPI, HostsAPI, HostGroupsAPI, ServiceDiscoveryAPI)
        provide domain-specific methods to perform actions such as activating changes, managing
        users and hosts, and running service discovery. These classes encapsulate the logic
        required to form, send, and process API requests.
    - Utility Functions: The module includes utility functions and context managers
        (e.g., wait_for_completion) to facilitate asynchronous operations by waiting for and
        processing HTTP redirects associated with long-running tasks.

"""

import itertools
import logging
import pprint
import time
import urllib.parse
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, NamedTuple

import requests

from cmk import trace
from cmk.gui.http import HTTPMethod
from cmk.gui.type_defs import KeyId
from cmk.gui.watolib.broker_connections import BrokerConnectionInfo
from cmk.relay_protocols.relays import RelayRegistrationRequest, RelayRegistrationResponse
from cmk.relay_protocols.tasks import (
    FetchAdHocTask,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskListResponse,
    TaskResponse,
)
from tests.testlib.version import CMKVersion, TypeCMKEdition, TypeCMKEditionOld

logger = logging.getLogger("rest-session")
tracer = trace.get_tracer()


class RestSessionException(Exception):
    pass


class UnexpectedResponse(RestSessionException):
    @classmethod
    def from_response(cls, response: requests.Response) -> "UnexpectedResponse":
        if 300 <= response.status_code < 400:
            text = f"Redirect to {response.headers['Location']}"
        else:
            text = response.text or repr(response)
        return cls(status_code=response.status_code, text=text)

    def __init__(self, status_code: int, text: str) -> None:
        super().__init__(f"[{status_code}] {text}")
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


class Relay(NamedTuple):
    id: str
    alias: str
    site_id: str
    num_fetchers: int | None
    log_level: str | None


class CMKOpenApiSession(requests.Session):
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        site_version: CMKVersion,
        site_edition: TypeCMKEdition | TypeCMKEditionOld,
        port: int = 80,
        site: str = "heute",
        api_version: str = "1.0",
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.site = site
        self.site_version = site_version
        self.site_edition = site_edition
        self.api_version = api_version
        self.headers["Accept"] = "application/json"
        self.set_authentication_header(user, password)

        self.changes = ChangesAPI(self)
        self.users = UsersAPI(self)
        self.user_role = UserRoleAPI(self)
        self.folders = FoldersAPI(self)
        self.hosts = HostsAPI(self)
        self.host_groups = HostGroupsAPI(self)
        self.host_tag_groups = HostTagGroupsAPI(self)
        self.service_discovery = ServiceDiscoveryAPI(self)
        self.services = ServicesAPI(self)
        self.agents = AgentsAPI(self)
        self.rules = RulesAPI(self)
        self.rulesets = RulesetsAPI(self)
        self.broker_connections = BrokerConnectionsAPI(self)
        self.bi_aggregation = BIAggregationAPI(self)
        self.sites = SitesAPI(self)
        self.background_jobs = BackgroundJobsAPI(self)
        self.dcd = DcdAPI(self)
        self.ldap_connection = LDAPConnectionAPI(self)
        self.passwords = PasswordsAPI(self)
        self.license = LicenseAPI(self)
        self.otel_collector = OtelCollectorAPI(self)
        self.event_console = EventConsoleAPI(self)
        self.saml2 = Saml2API(self)
        self.relays = RelayAPI(self)
        self.metric_backend = MetricBackendAPI(self)

    def set_authentication_header(self, user: str, password: str) -> None:
        self.headers["Authorization"] = f"Bearer {user} {password}"

    def request(  # type: ignore[override]
        self,
        method: str | bytes,
        url: str | bytes,
        *args: Any,
        timeout: float | tuple[float, float] | tuple[float, None] | None = 300.0,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Suggested method to use a base url with a requests.Session
        see https://github.com/psf/requests/issues/2554#issuecomment-109341010
        """
        assert isinstance(method, str)  # HACK
        assert isinstance(url, str)  # HACK
        kwargs["timeout"] = timeout

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

    @contextmanager
    def wait_for_completion(
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
        for attempt in itertools.count(start=1):
            if (running_time := time.time() - start) > timeout:
                msg = (
                    f"Wait for completion timed out after {running_time}s / {attempt} attempts"
                    f" for {operation}; URL={redirect_url}!"
                )
                if response and response.content:
                    msg += f"; Last response: {response.status_code}; {response.content!r}"
                raise TimeoutError(msg)

            logger.debug('Redirecting to "%s %s"...', http_method_for_redirection, redirect_url)
            response = self.request(
                method=http_method_for_redirection,
                url=redirect_url,
                allow_redirects=False,
            )
            if response.status_code == 204 and not response.content:
                logger.info(
                    "Wait for completion finished after %0.2fs / %s attempts for %s",
                    running_time,
                    attempt,
                    operation,
                )
                return

            if not 300 <= response.status_code < 400:
                raise UnexpectedResponse.from_response(response)

            time.sleep(0.5)


class AgentReceiverApiSession(requests.Session):
    def __init__(self, openapi_session: CMKOpenApiSession):
        super().__init__()
        self._openapi_session = openapi_session
        self._port: int | None = None
        self.headers["Authorization"] = self._openapi_session.headers["Authorization"]
        self.relays = AgentReceiverRelayAPI(self)
        self.verify = False

    def set_authentication_header(self, user: str, password: str) -> None:
        self.headers["Authorization"] = f"Bearer {user} {password}"

    @property
    def port(self) -> int:
        if self._port is None:
            self._port = int(
                self._openapi_session.get(
                    url="domain-types/internal/actions/discover-receiver/invoke",
                ).text
            )

        return self._port

    @property
    def base_url(self) -> str:
        return f"https://{self._openapi_session.host}:{self.port}/{self._openapi_session.site}/agent-receiver/"


class BaseAPI:
    def __init__(self, session: CMKOpenApiSession) -> None:
        self.session = session


class ARBaseAPI:
    def __init__(self, session: AgentReceiverApiSession) -> None:
        self.session = session


class ActivateStartResult(NamedTuple):
    activation_id: str
    redirect_url: str


class ChangesAPI(BaseAPI):
    def activate(
        self,
        sites: list[str] | None = None,
        force_foreign_changes: bool = False,
    ) -> ActivateStartResult:
        def _extract_activation_id_from_url(url: str) -> str:
            try:
                path_parts = urllib.parse.urlparse(response.headers["Location"]).path.split("/")
                return path_parts[path_parts.index("activation_run") + 1]
            except (ValueError, IndexError):
                raise ValueError(f"Failed to parse activation id from URL: {url}")

        response = self.session.post(
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

        if response.status_code == 422:
            raise NoActiveChanges  # there are no changes

        if response.status_code not in (302, 303):
            raise UnexpectedResponse.from_response(response)

        logger.info(
            "Activation id: %s",
            (activation_id := _extract_activation_id_from_url(response.headers["Location"])),
        )
        return ActivateStartResult(
            activation_id=activation_id,
            redirect_url=response.headers["Location"],
        )

    def get_pending(self) -> list[dict[str, Any]]:
        """Returns a list of all changes currently pending."""
        response = self.session.get("/domain-types/activation_run/collections/pending_changes")
        assert response.status_code == 200
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    @tracer.instrument("activate_and_wait_for_completion")
    def activate_and_wait_for_completion(
        self,
        sites: list[str] | None = None,
        force_foreign_changes: bool = False,
        timeout: int = 300,  # TODO: revert to 60 seconds once performance is improved.
        strict: bool = True,
    ) -> bool:
        """Activate changes via REST API and wait for completion.

        Returns:
            * True if changes are activated
            * False if there are no changes to be activated
        """
        pending_changes_ids_before = {_.get("id") for _ in self.get_pending()}

        logger.info("Activate changes and wait %ds for completion...", timeout)
        activation_id = None
        try:
            with self.session.wait_for_completion(timeout, "get", "activate_changes"):
                try:
                    start_result = self.activate(sites, force_foreign_changes)
                except NoActiveChanges:
                    return False
                else:
                    activation_id = start_result.activation_id
                    raise Redirect(start_result.redirect_url)
        finally:
            if activation_id:
                activation_status = self.get_activation_status(activation_id)
                if "status_per_site" in activation_status["extensions"]:
                    if not_succeeded_sites := [
                        status
                        for status in activation_status["extensions"]["status_per_site"]
                        if status["state"] != "success"
                    ]:
                        raise RuntimeError(
                            "Activation of the following sites did not succeed:\n"
                            f"{pprint.pformat(not_succeeded_sites)}"
                        )
                logger.info("Activation status: %s", str(pprint.pformat(activation_status)))

        # Suppression for mypy `unreachable` error is added here because this code could be actually
        # reached. Mypy does not realize that `wait_for_completion` context manager is swallowing
        # the `Redirect` exception.
        #
        # Mypy issue: https://github.com/python/mypy/issues/8766
        pending_changes_after = self.get_pending()  # type: ignore[unreachable]
        if strict:
            assert not pending_changes_after, (
                f"There are pending changes after activation: {pending_changes_after}"
            )
        else:
            pending_changes_intersection_ids = {
                _.get("id") for _ in pending_changes_after
            }.intersection(pending_changes_ids_before)
            assert not pending_changes_intersection_ids, (
                f"There are pending changes that were not activated: "
                f"{
                    (
                        _
                        for _ in pending_changes_after
                        if _.get('id') in pending_changes_intersection_ids
                    )
                }"
            )

        return True

    def get_activation_status(self, activation_id: str) -> dict[str, Any]:
        response = self.session.get(f"/objects/activation_run/{activation_id}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        json_data: dict[str, Any] = response.json()
        return json_data


class UsersAPI(BaseAPI):
    def create(
        self,
        username: str,
        fullname: str,
        password: str,
        email: str,
        contactgroups: list[str],
        roles: list[str] | None = None,
        is_automation_user: bool = False,
        store_automation_secret: bool = False,
    ) -> None:
        if is_automation_user:
            auth_option: dict[str, str | bool] = {
                "auth_type": "automation",
                "secret": password,
            }
            if store_automation_secret:
                # This attribute came during 2.4 development. We use this API for older versions as
                # well in test-update. So we should not set it in all requests!
                auth_option["store_automation_secret"] = True
        else:
            auth_option = {
                "auth_type": "password",
                "password": password,
            }

        body = {
            "username": username,
            "fullname": fullname,
            "auth_option": auth_option,
            "contact_options": {
                "email": email,
            },
            "contactgroups": contactgroups,
            "roles": roles or [],
        }
        if self.session.site_edition.is_ultimatemt_edition():
            body["customer"] = "global"
        response = self.session.post(
            "domain-types/user_config/collections/all",
            json=body,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def get_all(self) -> list[User]:
        response = self.session.get("domain-types/user_config/collections/all")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return [User(title=user_dict["title"]) for user_dict in response.json()["value"]]

    def get(self, username: str) -> tuple[dict[str, Any], str] | None:
        """
        Returns
            a tuple with the user details and the Etag header if the user was found
            None if the user was not found
        """
        response = self.session.get(f"/objects/user_config/{username}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def edit(self, username: str, user_spec: Mapping[str, Any], etag: str) -> None:
        response = self.session.put(
            f"objects/user_config/{username}",
            headers={
                "If-Match": etag,
            },
            json=user_spec,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def delete(self, username: str) -> None:
        response = self.session.delete(f"/objects/user_config/{username}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class UserRoleAPI(BaseAPI):
    """Wrap REST-API interface to interact with `user role`."""

    def delete(self, role_id: str) -> None:
        response = self.session.delete(f"/objects/user_role/{role_id}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class FoldersAPI(BaseAPI):
    def create(
        self,
        folder: str,
        title: str | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        # Convert folder path delimiters from '/' to '~' for the API
        folder_path = folder.replace("/", "~")
        # Ensure we are using the correct prefix
        folder_path = folder_path if folder_path.startswith("~") else f"~{folder_path}"

        parent_folder, folder_name = folder_path.rsplit("~", 1)
        parent_folder = parent_folder or "~"
        response = self.session.post(
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

    def get(self, folder: str) -> tuple[dict[Any, str], str] | None:
        """
        Returns
            a tuple with the folder details and the Etag header if the folder was found
            None if the folder was not found
        """
        response = self.session.get(f"/objects/folder_config/{folder.replace('/', '~')}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def delete(self, folder: str, delete_mode: str = "recursive") -> None:
        """Delete a folder.

        Args:
            folder: The path of the folder to delete. Path delimiters should be '/'.
            delete_mode: Delete policy. Options:
                - 'recursive': Deletes the folder and all elements it contains (default)
                - 'abort_on_nonempty': Deletes the folder only if it is empty
        Raises:
            UnexpectedResponse: If the delete operation fails
        """
        # Convert folder path delimiters from '/' to '~' for the API
        folder_path = folder.replace("/", "~")
        # Ensure we are using the correct prefix
        folder_path = folder_path if folder_path.startswith("~") else f"~{folder_path}"
        response = self.session.delete(
            f"/objects/folder_config/{folder_path}", params={"delete_mode": delete_mode}
        )

        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class HostsAPI(BaseAPI):
    def create(
        self,
        hostname: str,
        folder: str = "/",
        attributes: Mapping[str, Any] | None = None,
        bake_agent: bool = False,
    ) -> requests.Response:
        query_string = "?bake_agent=1" if bake_agent else ""
        response = self.session.post(
            f"/domain-types/host_config/collections/all{query_string}",
            json={"folder": folder, "host_name": hostname, "attributes": attributes or {}},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def bulk_create(
        self,
        entries: list[dict[str, Any]],
        bake_agent: bool = False,
        ignore_existing: bool = False,
    ) -> list[dict[str, Any]]:
        if ignore_existing:
            existing_hosts = self.get_all_names()
            entries = [_ for _ in entries if _.get("host_name") not in existing_hosts]
        query_string = "?bake_agent=1" if bake_agent else ""
        response = self.session.post(
            f"/domain-types/host_config/actions/bulk-create/invoke{query_string}",
            json={"entries": entries},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def get(self, hostname: str) -> tuple[dict[str, Any], str] | None:
        """
        Returns
            a tuple with the host details and the Etag header if the host was found
            None if the host was not found
        """
        response = self.session.get(f"/objects/host_config/{hostname}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def update(
        self,
        host_name: str,
        update_attributes: Mapping[str, object],
    ) -> None:
        response = self.session.put(
            url=f"/objects/host_config/{host_name}",
            json={"update_attributes": update_attributes},
            headers={
                "If-Match": "*",
                "Content-Type": "application/json",
            },
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def get_all(self) -> list[dict[str, Any]]:
        response = self.session.get(
            "/domain-types/host_config/collections/all", params={"include_links": False}
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def get_all_names(
        self, ignore: list[str] | None = None, allow: list[str] | None = None
    ) -> list[str]:
        """Get all host names from the API.

        Args:
            ignore: List of host names not to be returned, even if found in the system (optional).
            allow: List of host names to be returned, if found in the system (optional).
        """
        return [
            host_name
            for host_name in [host["id"] for host in self.get_all()]
            if (not ignore or host_name not in ignore) and (not allow or host_name in allow)
        ]

    def delete(self, hostname: str) -> None:
        response = self.session.delete(f"/objects/host_config/{hostname}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def bulk_delete(self, hostnames: list[str]) -> None:
        response = self.session.post(
            "/domain-types/host_config/actions/bulk-delete/invoke",
            json={"entries": hostnames},
        )
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def rename(self, *, hostname_old: str, hostname_new: str, etag: str) -> None:
        response = self.session.put(
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

    @tracer.instrument("rename_and_wait_for_completion")
    def rename_and_wait_for_completion(
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
        with self.session.wait_for_completion(timeout, "get", "rename_host"):
            self.rename(hostname_old=hostname_old, hostname_new=hostname_new, etag=etag)
            assert self.get(hostname_new) is not None, (
                'Failed to rename host "{hostname_old}" to "{hostname_new}"!'
            )

        response = self.session.background_jobs.show("rename-hosts")
        assert response["extensions"]["status"]["state"] == "finished", (
            f"Rename job failed: {response}"
        )


class HostGroupsAPI(BaseAPI):
    def create(self, name: str, alias: str) -> requests.Response:
        response = self.session.post(
            "/domain-types/host_group_config/collections/all",
            json={"name": name, "alias": alias},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def get(self, name: str) -> tuple[dict[Any, str], str]:
        response = self.session.get(f"/objects/host_group_config/{name}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def delete(self, name: str) -> None:
        response = self.session.delete(f"/objects/host_group_config/{name}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class HostTagGroupsAPI(BaseAPI):
    def create(self, name: str, title: str, tags: list[dict[str, str]]) -> requests.Response:
        response = self.session.post(
            "/domain-types/host_tag_group/collections/all",
            json={"id": name, "title": title, "tags": tags},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def get(self, name: str) -> tuple[dict[Any, str], str]:
        response = self.session.get(f"/objects/host_tag_group/{name}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def delete(self, name: str) -> None:
        response = self.session.delete(f"/objects/host_tag_group/{name}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class ServiceDiscoveryAPI(BaseAPI):
    def run_discovery(
        self,
        hostname: str,
        mode: str = "tabula_rasa",
    ) -> None:
        response = self.session.post(
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

    @tracer.instrument("run_bulk_discovery_and_wait_for_completion")
    def run_bulk_discovery_and_wait_for_completion(
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

        if self.session.site_version >= CMKVersion("2.3.0"):
            body["options"] = {
                "monitor_undecided_services": monitor_undecided_services,
                "remove_vanished_services": remove_vanished_services,
                "update_service_labels": update_service_labels,
                "update_host_labels": update_host_labels,
            }
        else:
            body["mode"] = "new"

        response = self.session.post(
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

        if status["extensions"]["status"]["state"] != "finished":
            raise RuntimeError(f"Discovery job {job_id} failed: {status}")

        output = "\n".join(status["extensions"]["status"]["log_info"]["JobProgressUpdate"])
        if "Traceback (most recent call last)" in output:
            raise RuntimeError(f"Found traceback in job output: {output}")
        if "0 failed" not in output:
            raise RuntimeError(f"Found a failure in job output: {output}")

        return job_id

    def get_bulk_discovery_status(self, job_id: str) -> str:
        job_status_response = self.get_bulk_discovery_job_status(job_id)
        status: str = job_status_response["extensions"]["status"]["state"]
        return status

    def get_bulk_discovery_job_status(self, job_id: str) -> dict[str, Any]:
        response = self.session.get(f"/objects/background_job/{job_id}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        json_data: dict[str, Any] = response.json()
        return json_data

    def get_discovery_status(self, hostname: str) -> str:
        job_status_response = self.get_discovery_job_status(hostname)

        if job_status_response["extensions"]["state"] == "exception":
            progress_log = job_status_response["extensions"]["logs"]["progress"]
            raise RuntimeError(f"Job failed with the following output:\n{'\n'.join(progress_log)}")

        status: str = job_status_response["extensions"]["state"]
        return status

    def get_discovery_job_status(self, hostname: str) -> dict[str, Any]:
        response = self.session.get(f"/objects/service_discovery_run/{hostname}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        json_data: dict[str, Any] = response.json()
        return json_data

    @tracer.instrument("run_discovery_and_wait_for_completion")
    def run_discovery_and_wait_for_completion(
        self, hostname: str, mode: str = "tabula_rasa", timeout: int = 60
    ) -> None:
        with self.session.wait_for_completion(timeout, "get", "discover_services"):
            self.run_discovery(hostname, mode)

        discovery_status = self.get_discovery_status(hostname)
        assert discovery_status == "finished", (
            f"Unexpected service discovery status: {discovery_status}"
        )

    def get_discovery_result(self, hostname: str) -> Mapping[str, object]:
        response = self.session.get(f"/objects/service_discovery/{hostname}")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return {str(k): v for k, v in response.json().items()}


class ServicesAPI(BaseAPI):
    def get_host_services(
        self, hostname: str, pending: bool | None = None, columns: list[str] | None = None
    ) -> list[dict[str, Any]]:
        if pending is not None:
            if columns is None:
                columns = ["has_been_checked"]
            elif "has_been_checked" not in columns:
                columns.append("has_been_checked")
        query_string = "?columns=" + "&columns=".join(columns) if columns else ""
        response = self.session.get(f"/objects/host/{hostname}/collections/services{query_string}")
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


class AgentsAPI(BaseAPI):
    def get_baking_status(self) -> BakingStatus:
        response = self.session.get("/domain-types/agent/actions/baking_status/invoke")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        result = response.json()["result"]["value"]
        return BakingStatus(
            state=result["state"],
            started=result["started"],
        )

    def sign(self, key_id: KeyId | str, passphrase: str) -> None:
        response = self.session.post(
            "/domain-types/agent/actions/sign/invoke",
            json={"key_id": key_id, "passphrase": passphrase},
        )
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class RulesAPI(BaseAPI):
    def create(
        self,
        value: object,
        ruleset_name: str | None = None,
        folder: str = "/",
        conditions: dict[str, Any] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> str:
        response = self.session.post(
            "/domain-types/rule/collections/all",
            json=(
                {
                    "ruleset": ruleset_name,
                    "folder": folder,
                    "value_raw": repr(value),
                    "conditions": conditions or {},
                    "properties": properties or {"disabled": False},
                }
                if ruleset_name
                else value
            ),
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        the_id: str = response.json()["id"]
        return the_id

    def get(self, rule_id: str) -> tuple[dict[Any, str], str] | None:
        """
        Returns
            a tuple with the rule details and the Etag header if the rule_id was found
            None if the rule_id was not found
        """
        response = self.session.get(f"/objects/rule/{rule_id}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None
        return (
            response.json()["extensions"],
            response.headers["Etag"],
        )

    def update(
        self,
        rule_id: str,
        value_raw: object | None = None,
        properties: dict[str, Any] | None = None,
        conditions: dict[str, Any] | None = None,
        etag: str = "*",
    ) -> None:
        """Update an existing rule."""
        update_data: dict[str, Any] = {}
        if value_raw is not None:
            update_data["value_raw"] = repr(value_raw)
        if properties is not None:
            update_data["properties"] = properties
        if conditions is not None:
            update_data["conditions"] = conditions

        response = self.session.put(
            f"/objects/rule/{rule_id}",
            json=update_data,
            headers={"If-Match": etag},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def delete(self, rule_id: str) -> None:
        response = self.session.delete(f"/objects/rule/{rule_id}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def get_all(
        self,
        ruleset_name: str | None = None,
        folder: str | None = None,
        include_extensions: bool = True,
    ) -> list[dict[str, Any]]:
        """Get all rules, optionally filtered by ruleset and folder."""
        params = {}
        if ruleset_name:
            params["ruleset_name"] = ruleset_name
        if folder:
            params["folder"] = folder
        if not include_extensions:
            params["include_extensions"] = "false"

        response = self.session.get(
            "/domain-types/rule/collections/all",
            params=params,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def get_all_names(self, ruleset_name: str) -> list[str]:
        return [_["id"] for _ in self.get_all(ruleset_name)]

    def move(
        self,
        rule_id: str,
        folder: str,
    ) -> None:
        """Move a rule to a different folder."""
        move_data = {"folder": folder}

        response = self.session.post(
            f"/objects/rule/{rule_id}/actions/move/invoke",
            json=move_data,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)


class RulesetsAPI(BaseAPI):
    def get_all(self) -> list[dict[str, Any]]:
        response = self.session.get(
            "/domain-types/ruleset/collections/all",
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def get_all_names(self) -> list[str]:
        return [_["id"] for _ in self.get_all()]


class BrokerConnectionsAPI(BaseAPI):
    def get_all(
        self,
    ) -> Sequence[Mapping[str, object]]:
        response = self.session.get(
            "/domain-types/broker_connection/collections/all",
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return [{str(k): v for k, v in el.items()} for el in response.json()["value"]]

    def create(self, connection_id: str, *, connecter: str, connectee: str) -> Mapping[str, object]:
        response = self.session.post(
            "/domain-types/broker_connection/collections/all",
            headers={
                "Content-Type": "application/json",
            },
            json={
                "connection_id": connection_id,
                "connection_config": BrokerConnectionInfo(
                    connecter={"site_id": connecter},
                    connectee={"site_id": connectee},
                ),
            },
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return {str(k): v for k, v in response.json().items()}

    def edit(self, connection_id: str, *, connecter: str, connectee: str) -> Mapping[str, object]:
        response = self.session.put(
            f"/objects/broker_connection/{connection_id}",
            headers={
                "Content-Type": "application/json",
            },
            json={
                "connection_config": BrokerConnectionInfo(
                    connecter={"site_id": connecter},
                    connectee={"site_id": connectee},
                ),
            },
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return {str(k): v for k, v in response.json().items()}

    def delete(self, connection_id: str) -> None:
        response = self.session.delete(
            f"/objects/broker_connection/{connection_id}",
            headers={
                "Content-Type": "application/json",
            },
        )
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class SitesAPI(BaseAPI):
    def create(self, site_config: dict[str, Any]) -> None:
        response = self.session.post(
            "/domain-types/site_connection/collections/all",
            headers={
                "Content-Type": "application/json",
            },
            json={"site_config": site_config},
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def update(self, site_id: str, site_config: dict[str, Any]) -> None:
        site_config.pop("logged_in", None)
        response = self.session.put(
            f"/objects/site_connection/{site_id}",
            headers={
                "Content-Type": "application/json",
            },
            json={"site_config": site_config},
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def show(self, site_id: str) -> dict[str, Any]:
        response = self.session.get(
            f"/objects/site_connection/{site_id}",
            headers={
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        value: dict[str, Any] = response.json()["extensions"]
        return value

    def delete(self, site_id: str) -> None:
        if (
            response := self.session.post(
                f"/objects/site_connection/{site_id}/actions/delete/invoke"
            )
        ).status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def login(self, site_id: str, user: str = "cmkadmin", password: str = "cmk") -> None:
        response = self.session.post(
            f"/objects/site_connection/{site_id}/actions/login/invoke",
            headers={
                "Content-Type": "application/json",
            },
            json={"username": user, "password": password},
        )

        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class BackgroundJobsAPI(BaseAPI):
    def show(self, job_id: str) -> dict[str, Any]:
        response = self.session.get(
            f"/objects/background_job/{job_id}",
            headers={
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        value: dict[str, Any] = response.json()
        return value


class BIAggregationAPI(BaseAPI):
    def get(self, aggregation_id: str) -> dict[str, Any]:
        response = self.session.get(
            f"/objects/bi_aggregation/{aggregation_id}",
            headers={
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        value: dict[str, Any] = response.json()
        return value

    def update(self, aggregation_id: str, body: dict[str, Any]) -> None:
        response = self.session.put(
            f"/objects/bi_aggregation/{aggregation_id}",
            headers={
                "Content-Type": "application/json",
            },
            json=body,
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def delete(self, aggregation_id: str) -> None:
        response = self.session.delete(
            f"/objects/bi_aggregation/{aggregation_id}",
            headers={
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def create(self, aggregation_id: str, body: dict[str, Any]) -> None:
        response = self.session.post(
            f"/objects/bi_aggregation/{aggregation_id}",
            headers={
                "Content-Type": "application/json",
            },
            json=body,
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)


@dataclass(frozen=True, kw_only=True)
class MetricBackendDCDConnectionAttributeFilter:
    key: str
    value: str


class DcdAPI(BaseAPI):
    def __init__(self, session: CMKOpenApiSession):
        super().__init__(session)
        self._base_url_internal = f"http://{self.session.host}:{self.session.port}/{self.session.site}/check_mk/api/internal"

    def create_piggyback_connection(
        self,
        dcd_id: str,
        title: str,
        comment: str = "",
        disabled: bool = False,
        restrict_source_hosts: list[str] | None = None,
        interval: int = 60,
        host_attributes: dict[str, object] | None = None,
        delete_hosts: bool = False,
        discover_on_creation: bool = True,
        no_deletion_time_after_init: int = 600,
        max_cache_age: int = 3600,
        validity_period: int = 60,
    ) -> None:
        """Create a DCD connection via REST API."""
        resp = self.session.post(
            "/domain-types/dcd/collections/all",
            json={
                "dcd_id": dcd_id,
                "title": title,
                "comment": comment,
                "disabled": disabled,
                "site": self.session.site,
                "connector": {
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
            },
        )
        if resp.status_code != 200:
            raise UnexpectedResponse.from_response(resp)

    def create_metric_backend_connection(
        self,
        *,
        dcd_id: str,
        title: str,
        interval: int = 60,
        host_name_resource_attribute_key: str,
        resource_attribute_filters: Sequence[MetricBackendDCDConnectionAttributeFilter] = (),
        scope_attribute_filters: Sequence[MetricBackendDCDConnectionAttributeFilter] = (),
        data_point_attribute_filters: Sequence[MetricBackendDCDConnectionAttributeFilter] = (),
        delete_hosts: bool = False,
        discover_on_creation: bool = True,
        validity_period: int = 60,
        maximum_number_of_hosts: int = 500,
    ) -> None:
        """Create a DCD connection via REST API."""
        response = self.session.post(
            f"{self._base_url_internal}/domain-types/dcd_metric_backend/collections/all",
            json={
                "dcd_id": dcd_id,
                "title": title,
                "site": self.session.site,
                "connector": {
                    "connector_type": "metric_backend",
                    "interval": interval,
                    "resource_attribute_filters": [
                        {
                            "key": attribute_filter.key,
                            "value": attribute_filter.value,
                        }
                        for attribute_filter in resource_attribute_filters
                    ],
                    "scope_attribute_filters": [
                        {
                            "key": attribute_filter.key,
                            "value": attribute_filter.value,
                        }
                        for attribute_filter in scope_attribute_filters
                    ],
                    "data_point_attribute_filters": [
                        {
                            "key": attribute_filter.key,
                            "value": attribute_filter.value,
                        }
                        for attribute_filter in data_point_attribute_filters
                    ],
                    "host_name_resource_attribute_key": host_name_resource_attribute_key,
                    "creation_rules": [
                        {
                            "folder_path": "/",
                            "host_attributes": {
                                "tag_address_family": "no-ip",
                                "tag_agent": "special-agents",
                            },
                            "delete_hosts": delete_hosts,
                        }
                    ],
                    "discover_on_creation": discover_on_creation,
                    "validity_period": validity_period,
                    "maximum_number_of_hosts": maximum_number_of_hosts,
                },
            },
        )
        if not response.ok:
            raise UnexpectedResponse.from_response(response)

    def get(self, dcd_id: str) -> dict[str, Any] | None:
        """
        Returns
            the DCD details if the dcd_id was found
            None if the dcd_id was not found
        """
        response = self.session.get(f"/objects/dcd/{dcd_id}")
        if response.status_code not in (200, 404):
            raise UnexpectedResponse.from_response(response)
        if response.status_code == 404:
            return None

        json_data: dict[str, Any] = response.json()
        return json_data

    def delete(self, dcd_id: str) -> None:
        """Delete a DCD connection via REST API."""
        resp = self.session.delete(f"/objects/dcd/{dcd_id}")
        if resp.status_code != 204:
            raise UnexpectedResponse.from_response(resp)


class LDAPConnectionAPI(BaseAPI):
    def create(
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

        resp = self.session.post(
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

    def delete(self, ldap_id: str) -> None:
        """Delete an LDAP connection via REST API."""
        resp = self.session.delete(f"/objects/ldap_connection/{ldap_id}", headers={"If-Match": "*"})
        if resp.status_code != 204:
            raise UnexpectedResponse.from_response(resp)


class PasswordsAPI(BaseAPI):
    def create(
        self,
        ident: str,
        title: str,
        comment: str,
        password: str,
        owner: str = "admin",
    ) -> None:
        """Create a password via REST API."""

        request_data = {
            "ident": ident,
            "title": title,
            "comment": comment,
            "documentation_url": "localhost",
            "password": password,
            "owner": owner,
            "shared": ["all"],
        }
        if self.session.site_edition.is_ultimatemt_edition():
            request_data["customer"] = "global"

        response = self.session.post(
            "/domain-types/password/collections/all",
            json=request_data,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def delete(
        self,
        ident: str,
    ) -> None:
        """Delete a password via REST API."""
        response = self.session.delete(f"/objects/password/{ident}", headers={"If-Match": "*"})

        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def get_all(self) -> list[dict[str, Any]]:
        """Get all configured passwords via REST API."""
        response = self.session.get(
            "/domain-types/password/collections/all", headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def exists(self, ident: str) -> bool:
        """Check if a password exists via REST API."""
        raw_passwords = self.get_all()
        return any(pw["id"] == ident for pw in raw_passwords)


class LicenseAPI(BaseAPI):
    def configure(self, settings: Mapping[str, str | Mapping[str, str]]) -> requests.Response:
        response = self.session.put(
            "/domain-types/licensing/actions/configure/invoke",
            json={"settings": settings} if settings else {},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def download(self) -> requests.Response:
        response = self.session.get("/domain-types/license_request/actions/download/invoke")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def upload(self, verification_response: object) -> requests.Response:
        response = self.session.post(
            url="/domain-types/license_response/actions/upload/invoke",
            json=verification_response,
        )
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)
        return response

    def verify(self) -> requests.Response:
        """Trigger the license verification and receive its results"""
        response = self.session.post("/domain-types/licensing/actions/verify/invoke")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)
        return response


class OtelCollectorAPI(BaseAPI):
    def __init__(self, session: CMKOpenApiSession) -> None:
        super().__init__(session)
        # Hack to use the "internal" version of the API endpoint
        self.base_url = f"http://{self.session.host}:{self.session.port}/{self.session.site}/check_mk/api/internal"

    def get_receivers(self, expect_ok: bool = True) -> requests.Response:
        """Get all OpenTelemetry collector receivers via REST API."""
        response = self.session.get(
            url=self.base_url + "/domain-types/otel_collector_config_receivers/collections/all",
        )
        if expect_ok and response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def get_prom_scrapers(self, expect_ok: bool = True) -> requests.Response:
        """Get all OpenTelemetry collector prometheus scrapiers via REST API."""
        response = self.session.get(
            url=self.base_url + "/domain-types/otel_collector_config_prom_scrape/collections/all",
        )
        if expect_ok and response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def create_receivers(
        self,
        ident: str,
        site_ids: Sequence[str],
        title: str,
        disabled: bool,
        receiver_protocol_grpc: dict[str, Any] | None = None,
        receiver_protocol_http: dict[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> requests.Response:
        """Create an OpenTelemetry collector receivers via REST API."""
        body = {
            "id": ident,
            "disabled": disabled,
            "site": site_ids,
            "title": title,
        }
        if receiver_protocol_grpc:
            body["receiver_protocol_grpc"] = receiver_protocol_grpc
        if receiver_protocol_http:
            body["receiver_protocol_http"] = receiver_protocol_http

        response = self.session.post(
            url=self.base_url + "/domain-types/otel_collector_config_receivers/collections/all",
            json=body,
        )
        if expect_ok and response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def create_prom_scrape(
        self,
        ident: str,
        site_ids: Sequence[str],
        title: str,
        disabled: bool,
        prometheus_scrape_configs: list[dict[str, Any]] | None = None,
        expect_ok: bool = True,
    ) -> requests.Response:
        """Create an OpenTelemetry collector prometheus scraping config via REST API."""
        body = {
            "id": ident,
            "disabled": disabled,
            "site": site_ids,
            "title": title,
        }
        if prometheus_scrape_configs:
            body["prometheus_scrape_configs"] = prometheus_scrape_configs

        # hack to use the "internal" version of the API endpoint
        response = self.session.post(
            url=self.base_url + "/domain-types/otel_collector_config_prom_scrape/collections/all",
            json=body,
        )
        if expect_ok and response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def edit_receivers(
        self,
        ident: str,
        site_ids: Sequence[str],
        title: str | None = None,
        disabled: bool | None = None,
        receiver_protocol_grpc: dict[str, Any] | None = None,
        receiver_protocol_http: dict[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> requests.Response:
        """Edit an OpenTelemetry collector receiver via REST API."""

        body: dict[str, Any] = {
            "id": ident,
            "disabled": disabled,
            "site": site_ids,
            "title": title,
        }

        if receiver_protocol_grpc:
            body["receiver_protocol_grpc"] = receiver_protocol_grpc
        if receiver_protocol_http:
            body["receiver_protocol_http"] = receiver_protocol_http

        response = self.session.put(
            url=self.base_url + f"/objects/otel_collector_config_receivers/{ident}",
            json=body,
        )
        if expect_ok and response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def edit_prom_scrape(
        self,
        ident: str,
        site_ids: Sequence[str],
        title: str | None = None,
        disabled: bool | None = None,
        prometheus_scrape_configs: list[dict[str, Any]] | None = None,
        expect_ok: bool = True,
    ) -> requests.Response:
        """Edit an OpenTelemetry collector prometheus scraping via REST API."""

        body: dict[str, Any] = {
            "id": ident,
            "disabled": disabled,
            "site": site_ids,
            "title": title,
        }

        if prometheus_scrape_configs:
            body["prometheus_scrape_configs"] = prometheus_scrape_configs

        response = self.session.put(
            url=self.base_url + f"/objects/otel_collector_config_prom_scrape/{ident}",
            json=body,
        )
        if expect_ok and response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return response

    def delete_receivers(self, ident: str, expect_ok: bool = True) -> requests.Response:
        """Delete an OpenTelemetry collector receiver via REST API."""
        response = self.session.delete(
            self.base_url + f"/objects/otel_collector_config_receivers/{ident}"
        )
        if expect_ok and response.status_code != 204:
            raise UnexpectedResponse.from_response(response)
        return response

    def delete_prom_scrape(self, ident: str, expect_ok: bool = True) -> requests.Response:
        """Delete an OpenTelemetry collector prometheus scraping via REST API."""
        response = self.session.delete(
            self.base_url + f"/objects/otel_collector_config_prom_scrape/{ident}"
        )
        if expect_ok and response.status_code != 204:
            raise UnexpectedResponse.from_response(response)
        return response

    def disable(self, site_id: str) -> requests.Response:
        response = self.session.put(
            url=self.base_url + "/domain-types/otel_collector/actions/update/invoke",
            json={"site_id": site_id, "activation": {"mode": "disabled"}},
        )
        if not response.ok:
            raise UnexpectedResponse.from_response(response)
        return response

    def enable(self, site_id: str) -> requests.Response:
        response = self.session.put(
            url=self.base_url + "/domain-types/otel_collector/actions/update/invoke",
            json={"site_id": site_id, "activation": {"mode": "enabled"}},
        )
        if not response.ok:
            raise UnexpectedResponse.from_response(response)
        return response


class EventConsoleAPI(BaseAPI):
    def get_all(self) -> list[dict[str, Any]]:
        response = self.session.get(
            "/domain-types/event_console/collections/all",
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        value: list[dict[str, Any]] = response.json()["value"]
        return value

    def archive_events_by_params(self, filters: dict[str, Any]) -> None:
        """Archive EC events by using 'params' filter type."""
        body = {"filter_type": "params", "filters": filters}
        response = self.session.post(
            url="/domain-types/event_console/actions/delete/invoke", json=body
        )
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class Saml2API(BaseAPI):
    def get_all(self) -> list[dict[str, Any]]:
        response = self.session.get("/domain-types/saml_connection/collections/all")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        saml_connections: list[dict[str, Any]] = response.json()["value"]
        return saml_connections

    def get(self, connection_id: str) -> tuple[dict[str, Any], str]:
        """Returns a tuple with the connection details and the Etag header"""
        response = self.session.get(f"/objects/saml_connection/{connection_id}")

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        return (response.json()["extensions"], response.headers["Etag"])

    def create(self, connection_id: str, connection_config: dict[str, Any]) -> dict[str, Any]:
        connection = {
            "general_properties": {
                "id": connection_id,
                "name": "Test SAML Auth",
            },
            "connection_config": connection_config,
            "security": {
                "signing_certificate": {"type": "builtin"},
                "decrypt_auth_certificate": {"type": "builtin"},
            },
            "users": {
                "id_attribute": "user_id",
            },
        }

        response = self.session.post(
            "/domain-types/saml_connection/collections/all",
            json=connection,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        json_data: dict[str, Any] = response.json()
        return json_data

    def delete(self, connection_id: str, etag: str) -> None:
        response = self.session.delete(
            f"/objects/saml_connection/{connection_id}",
            headers={"If-Match": etag},
        )

        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class RelayAPI(BaseAPI):
    _domain_url = "/domain-types/relay/collections/all"
    _headers = {"Content-Type": "application/json"}

    @staticmethod
    def _object_url(relay_id: str) -> str:
        return f"/objects/relay/{relay_id}"

    def create(
        self,
        alias: str,
        site_id: str,
        num_fetchers: int = 13,
        log_level: str = "INFO",
    ) -> None:
        response = self.session.post(
            url=self._domain_url,
            headers=self._headers,
            json={
                "alias": alias,
                "siteid": site_id,
                "num_fetchers": num_fetchers,
                "log_level": log_level,
            },
        )

        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def get(self, relay_id: str) -> tuple[Relay, str]:
        response = self.session.get(
            url=self._object_url(relay_id),
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        response_json = response.json()
        return Relay(
            id=relay_id,
            alias=response_json["extensions"]["alias"],
            site_id=response_json["extensions"]["siteid"],
            num_fetchers=response_json["extensions"]["num_fetchers"],
            log_level=response_json["extensions"]["log_level"],
        ), response.headers["Etag"]

    def get_all(self) -> list[Relay]:
        response = self.session.get(url=self._domain_url)
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return [
            Relay(
                id=relay_dict["id"],
                alias=relay_dict["extensions"]["alias"],
                site_id=relay_dict["extensions"]["siteid"],
                num_fetchers=relay_dict["extensions"]["num_fetchers"],
                log_level=relay_dict["extensions"]["log_level"],
            )
            for relay_dict in response.json()["value"]
        ]

    def edit(self, relay: Relay) -> None:
        response = self.session.put(
            url=self._object_url(relay.id),
            json={
                "alias": relay.alias,
                "siteid": relay.site_id,
                "num_fetchers": relay.num_fetchers,
                "log_level": relay.log_level,
            },
            headers={"If-Match": "*"},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def delete(self, relay_id: str, etag: str) -> None:
        response = self.session.delete(
            url=self._object_url(relay_id),
            headers={"If-Match": etag},
        )
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)


class MetricBackendAPI(BaseAPI):
    def __init__(self, session: CMKOpenApiSession):
        super().__init__(session)
        self._base_url_internal = f"http://{self.session.host}:{self.session.port}/{self.session.site}/check_mk/api/internal"

    def disable(self, site_id: str) -> None:
        response = self.session.put(
            url=self._config_endpoint_url(),
            json={
                "site_id": site_id,
                "config": {
                    "type": "disabled",
                },
            },
        )

        if not response.ok:
            raise UnexpectedResponse.from_response(response)

    def enable(self, site_id: str) -> None:
        response = self.session.put(
            url=self._config_endpoint_url(),
            json={
                "site_id": site_id,
                "config": {
                    "type": "enabled",
                },
            },
        )

        if not response.ok:
            raise UnexpectedResponse.from_response(response)

    def _config_endpoint_url(self) -> str:
        return f"{self._base_url_internal}/domain-types/metric_backend/actions/update/invoke"


class AgentReceiverRelayAPI(ARBaseAPI):
    @property
    def base_url(self) -> str:
        return f"https://{self.session._openapi_session.host}:{self.session.port}/{self.session._openapi_session.site}/"

    def register(self, relay_id: str, alias: str, csr: str) -> RelayRegistrationResponse:
        body = RelayRegistrationRequest(relay_id=relay_id, alias=alias, csr=csr)
        response = self.session.post(
            url=urllib.parse.urljoin(self.base_url, "relays/"),
            json=body.model_dump(),
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        return RelayRegistrationResponse.model_validate(response.json())

    def unregister(self, relay_id: str) -> None:
        response = self.session.delete(
            url=urllib.parse.urljoin(self.base_url, f"relays/{relay_id}")
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def put_task(self, relay_id: str, task: FetchAdHocTask) -> TaskCreateResponse:
        response = self.session.post(
            url=urllib.parse.urljoin(self.base_url, f"relays/{relay_id}/tasks"),
            json=TaskCreateRequest(spec=task).model_dump(),
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return TaskCreateResponse.model_validate(response.json())

    def get_tasks(self, relay_id: str, cert: tuple[str, str]) -> list[TaskResponse]:
        response = self.session.get(
            url=urllib.parse.urljoin(self.base_url, f"relays/{relay_id}/tasks"),
            cert=cert,
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return TaskListResponse.model_validate(response.json()).tasks
