#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module defines various classes and functions for handling REST API requests in Checkmk.

It includes clients for different API domains, providing methods to perform create, read, update,
delete operations and other actions.
"""

from __future__ import annotations

import abc
import dataclasses
import datetime
import json
import pprint
import time
import urllib.parse
from collections.abc import Mapping, Sequence
from typing import Any, cast, Literal, NoReturn, NotRequired, Self, TYPE_CHECKING, TypedDict

from cmk.ccc import version

from cmk.utils import paths

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.endpoints.configuration_entity._common import to_domain_type
from cmk.gui.openapi.endpoints.contact_group_config.common import APIInventoryPaths
from cmk.gui.rest_api_types.notifications_rule_types import APINotificationRule
from cmk.gui.rest_api_types.site_connection import SiteConfig
from cmk.gui.type_defs import DismissableWarning

from cmk.shared_typing.configuration_entity import ConfigEntityType

if TYPE_CHECKING:
    from cmk.gui.openapi.endpoints.downtime import FindByType

JSON = int | str | bool | list[Any] | dict[str, Any] | None
JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
IF_MATCH_HEADER_OPTIONS = Literal["valid_etag", "invalid_etag", "star"] | None

API_DOMAIN = Literal[
    "configuration_entity",
    "licensing",
    "activation_run",
    "user_config",
    "host",
    "host_config",
    "folder_config",
    "aux_tag",
    "time_period",
    "rule",
    "ruleset",
    "host_tag_group",
    "password",
    "agent",
    "downtime",
    "host_group_config",
    "service_group_config",
    "contact_group_config",
    "site_connection",
    "notification_rule",
    "comment",
    "event_console",
    "audit_log",
    "bi_pack",
    "bi_aggregation",
    "bi_rule",
    "user_role",
    "autocomplete",
    "service",
    "service_discovery",
    "discovery_run",
    "ldap_connection",
    "saml_connection",
    "parent_scan",
    "quick_setup",
    "quick_setup_stage",
    "managed_robots",
    "notification_parameter",
    "broker_connection",
    "background_job",
    "acknowledge",
    "otel_collector_config",
]


def _only_set_keys(body: dict[str, Any | None]) -> dict[str, Any]:
    return {k: v for k, v in body.items() if v is not None}


def set_if_match_header(
    if_match: IF_MATCH_HEADER_OPTIONS,
) -> Mapping[str, str] | None:
    match if_match:
        case "star":
            return {"If-Match": "*"}
        case "invalid_etag":
            return {"If-Match": "asdf"}
        case _:
            return None


@dataclasses.dataclass(frozen=True)
class Response:
    status_code: int
    body: bytes | None
    headers: Mapping[str, str]  # TODO: Use werkzeug.datastructures.Headers?

    def assert_status_code(self, status_code: int) -> Response:
        assert self.status_code == status_code
        return self

    @property
    def json(self) -> Any:
        assert self.body is not None
        return json.loads(self.body.decode("utf-8"))

    def assert_rest_api_crash(self) -> Self:
        """Assert that the response is a REST API crash report. Then delete the underlying file."""
        assert self.status_code == 500
        assert_and_delete_rest_crash_report(self.json["ext"]["id"])
        return self


def assert_and_delete_rest_crash_report(crash_id: str) -> None:
    """Assert that the REST API crash report with the given ID exists and delete it."""
    crash_file = paths.crash_dir / "rest_api" / crash_id / "crash.info"
    assert crash_file.exists()
    crash_file.unlink()


class RestApiRequestException(Exception):
    def __init__(
        self,
        url: str,
        method: str,
        body: Any | None = None,
        headers: Mapping[str, str] | None = None,
        query_params: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(url, method, body, headers)
        self.url = url
        self.query_params = query_params
        self.method = method
        self.body = body
        self.headers = headers

    def __str__(self) -> str:
        return pprint.pformat(
            {
                "request": {
                    "method": self.method,
                    "url": self.url,
                    "query_params": self.query_params,
                    "body": self.body,
                    "headers": self.headers,
                },
            },
            compact=True,
        )


class RestApiException(Exception):
    def __init__(
        self,
        url: str,
        method: str,
        body: Any,
        headers: Mapping[str, str],
        response: Response,
        query_params: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(url, method, body, headers, response)
        self.url = url
        self.query_params = query_params
        self.method = method
        self.body = body
        self.headers = headers
        self.response = response

    def __str__(self) -> str:
        try:
            formatted_body = json.loads(cast(bytes, self.response.body))
        except (ValueError, TypeError):
            formatted_body = self.response.body

        return pprint.pformat(
            {
                "request": {
                    "method": self.method,
                    "url": self.url,
                    "query_params": self.query_params,
                    "body": self.body,
                    "headers": self.headers,
                },
                "response": {
                    "status": self.response.status_code,
                    "body": formatted_body,
                    "headers": self.response.headers,
                },
            },
            compact=True,
        )


def get_link(resp: dict, rel: str) -> Mapping:
    """Return the first instance of 'link' corresponding to pattern 'rel'.

    Searches recursively within the dictionary.
    """
    for key, value in resp.items():
        if key == "members" and value.get("memberType", "") != "action":
            continue
        if key == "links" and isinstance(value, list):
            for link in value:
                if link.get("rel", "").startswith(rel):
                    return link
        elif isinstance(value, dict):
            try:
                return get_link(value, rel)
            except KeyError:
                continue
    raise KeyError(f"No 'link' found corresponding to 'rel' pattern: '{rel}'!")


def expand_rel(rel: str) -> str:
    if rel.startswith(".../"):
        rel = rel.replace(".../", "urn:org.restfulobjects:rels/")
    if rel.startswith("cmk/"):
        rel = rel.replace("cmk/", "urn:com.checkmk:rels/")
    return rel


class RequestHandler(abc.ABC):
    """A class representing a way to do HTTP Requests."""

    @abc.abstractmethod
    def set_credentials(self, username: str, password: str) -> None: ...

    @abc.abstractmethod
    def request(
        self,
        method: HTTPMethod,
        url: str,
        query_params: Mapping[str, Any] | None = None,
        body: str | None = None,
        headers: Mapping[str, str] | None = None,
        follow_redirects: bool = False,
    ) -> Response: ...


# types used in RestApiClient
class TimeRange(TypedDict):
    start: str
    end: str


class RuleProperties(TypedDict, total=False):
    description: str
    comment: str
    documentation_url: str
    disabled: bool


def default_rule_properties() -> RuleProperties:
    return {"disabled": False}


class StringMatcher(TypedDict, total=False):
    match_on: list[str]
    operator: Literal["one_of", "none_of"]


class HostTagMatcher(TypedDict):
    key: str
    operator: Literal["is", "is_not", "none_of", "one_if"]
    value: str


class LabelMatcher(TypedDict):
    key: str
    operator: Literal["is", "is_not"]
    value: str


class LabelCondition(TypedDict):
    operator: Literal["and", "or", "not"]
    label: str


class LabelGroupCondition(TypedDict):
    operator: NotRequired[Literal["and", "or", "not"]]
    label_group: list[LabelCondition]


class RuleConditions(TypedDict, total=False):
    host_name: StringMatcher
    host_tags: list[HostTagMatcher]
    host_label_groups: list[LabelGroupCondition]
    service_label_groups: list[LabelGroupCondition]
    host_labels: list[LabelMatcher]
    service_labels: list[LabelMatcher]
    service_description: StringMatcher


class RestApiClient:
    """API Client for the REST API.

    This class offers convenient methods for accessing the REST API.
    Not that this is (as of now) not intended to be able to handle all endpoints the REST API provides,
    instead it makes assumptions in the name of usability that hold true for almost all the API.
    Also, as of now this is far away from being a complete wrapper for the API, so please add
    functions as you need them.

    The general pattern for adding functions for an endpoint is:
    * inline all path params as function parameters
    * inline the top level keys of the request body as function parameters
    * inline all query parameters as function parameters
    * add the following arg: `expect_ok: bool = True`
    * call and return `self.request()` with the following args:
      * `url` should be the url of the endpoint with all path parameters filled in
      * `body` should be a dict with all the keys you inlined in to the function signature
      * `query_params` should be a dict with all the query parameters you inlined into the function signature
      * `expect_ok` should be passed on from the function signature
    * if the endpoint needs an etag, get it and pass it as a header to `self.request()` (see `edit_host`)

    A good example to start from would be the `create_host` method of this class.

    Please feel free to shuffle or convert function arguments if you believe it will increase the usability of the client.
    """

    def __init__(self, request_handler: RequestHandler, url_prefix: str):
        self.request_handler = request_handler
        self._url_prefix = url_prefix

    def set_credentials(self, username: str, password: str) -> None:
        self.request_handler.set_credentials(username, password)

    # This is public for quick debugging sessions
    def request(
        self,
        method: HTTPMethod,
        url: str,
        body: JSON | None = None,
        query_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        expect_ok: bool = True,
        follow_redirects: bool = True,
        url_is_complete: bool = False,
        use_default_headers: bool = True,
        redirect_timeout_seconds: int = 60,
    ) -> Response:
        default_headers: Mapping[str, str] = {
            **(JSON_HEADERS if use_default_headers else {}),
            **({} if headers is None else headers),
        }

        if not url_is_complete:
            url = self._url_prefix + url

        req_body = None if body is None else json.dumps(body)
        resp = self.request_handler.request(
            method=method,
            url=url,
            query_params=query_params,
            body=req_body,
            headers=default_headers,
            follow_redirects=False,  # we handle redirects ourselves
        )
        if follow_redirects:
            end = time.time() + redirect_timeout_seconds
            while 300 <= resp.status_code < 400:
                if time.time() > end:
                    raise TimeoutError("Redirect timeout reached")

                if resp.status_code == 303:
                    # 303 See Other: we should explicitly use GET for the redirect
                    # other redirect codes should reuse the method of the original request
                    method = "get"
                    req_body = None

                resp = self.request_handler.request(
                    method=method,
                    url=self._get_redirect_url(resp.headers["Location"]),
                    query_params=query_params,
                    body=req_body,
                    headers=default_headers,
                    follow_redirects=False,
                )

        if expect_ok and resp.status_code >= 400:
            raise RestApiException(
                url, method, body, default_headers, resp, query_params=query_params
            )
        return resp

    def _get_redirect_url(self, location_header: str) -> str:
        prefix = urllib.parse.urlparse(self._url_prefix)
        location = urllib.parse.urlparse(location_header)
        return urllib.parse.urlunparse(
            (
                location.scheme or prefix.scheme,
                location.netloc or prefix.netloc,
                location.path,
                location.params,
                location.query,
                location.fragment,
            )
        )

    def follow_link(
        self,
        links: dict[str, Any],
        relation: str,
        extra_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        params = extra_params or {}
        body = {}
        link = get_link(links, expand_rel(relation))
        if "body_params" in link and link["body_params"]:
            assert isinstance(link["body_params"], dict)  # for mypy
            body.update(link["body_params"])
        body.update(params)
        kwargs = {
            "method": link["method"],
            "url": link["href"],
            "body": body,
            "headers": headers,
        }
        if not body:
            del kwargs["body"]
        return self.request(**kwargs, url_is_complete=True, expect_ok=expect_ok)

    def get_graph(
        self,
        host_name: str,
        service_description: str,
        type_: Literal["single_metric", "graph"],
        time_range: TimeRange,
        graph_or_metric_id: str,
        site: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body = {
            "host_name": host_name,
            "service_description": service_description,
            "type": type_,
            "time_range": time_range,
        }
        if type_ == "graph":
            body["graph_id"] = graph_or_metric_id
        if type_ == "single_metric":
            body["metric_id"] = graph_or_metric_id

        if site is not None:
            body["site"] = site

        return self.request(
            "post",
            url="/domain-types/metric/actions/get/invoke",
            body=body,
            expect_ok=expect_ok,
        )


class LicensingClient(RestApiClient):
    domain: API_DOMAIN = "licensing"

    def call_online_verification(self, expect_ok: bool = False) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/verify/invoke",
            expect_ok=expect_ok,
        )

    def call_configure_licensing_settings(
        self, settings: Mapping[str, str | Mapping[str, str]], expect_ok: bool = False
    ) -> Response:
        body = {"settings": settings} if settings else {}
        return self.request(
            "put",
            url=f"/domain-types/{self.domain}/actions/configure/invoke",
            body=body,
            expect_ok=expect_ok,
        )

    def call_download_license_request(self, expect_ok: bool = False) -> Response:
        return self.request(
            "get",
            url="/domain-types/license_request/actions/download/invoke",
            expect_ok=expect_ok,
        )

    def call_verify_offline(
        self, verification_response: dict[str, Any], expect_ok: bool = False
    ) -> Response:
        return self.request(
            "post",
            url="/domain-types/license_response/actions/upload/invoke",
            body=verification_response,
            expect_ok=expect_ok,
        )


class ActivateChangesClient(RestApiClient):
    domain: API_DOMAIN = "activation_run"

    def get_activation(self, activation_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{activation_id}",
            expect_ok=expect_ok,
        )

    def get_running_activations(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/running",
            expect_ok=expect_ok,
        )

    def activate_changes(
        self,
        sites: list[str] | None = None,
        redirect: bool = False,
        force_foreign_changes: bool = False,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        if sites is None:
            sites = []
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/activate-changes/invoke",
            body={
                "redirect": redirect,
                "sites": sites,
                "force_foreign_changes": force_foreign_changes,
            },
            headers=self._set_etag_header(etag),
            expect_ok=expect_ok,
        )

    def call_activate_changes_and_wait_for_completion(
        self,
        sites: list[str] | None = None,
        force_foreign_changes: bool = False,
        timeout_seconds: int = 60,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response | NoReturn:
        if sites is None:
            sites = []
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/activate-changes/invoke",
            body={
                "redirect": True,
                "sites": sites,
                "force_foreign_changes": force_foreign_changes,
            },
            expect_ok=True,
            headers=self._set_etag_header(etag),
            follow_redirects=True,
            redirect_timeout_seconds=timeout_seconds,
        )

    def list_pending_changes(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/pending_changes",
            expect_ok=expect_ok,
        )

    def _set_etag_header(self, etag: IF_MATCH_HEADER_OPTIONS) -> Mapping[str, str] | None:
        if etag == "valid_etag":
            return {"If-Match": self.list_pending_changes().headers["ETag"]}
        return set_if_match_header(etag)


class UserClient(RestApiClient):
    domain: API_DOMAIN = "user_config"

    def create(
        self,
        username: str,
        fullname: str,
        customer: str | None = None,
        authorized_sites: Sequence[str] | None = None,
        contactgroups: Sequence[str] | None = None,
        auth_option: dict[str, Any] | None = None,
        roles: list[str] | None = None,
        idle_timeout: dict[str, Any] | None = None,
        interface_options: dict[str, str] | None = None,
        disable_notifications: dict[str, Any] | None = None,
        disable_login: bool | None = None,
        pager_address: str | None = None,
        language: str | None = None,
        temperature_unit: str | None = None,
        contact_options: dict[str, Any] | None = None,
        start_url: str | None = None,
        extra: dict[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        if extra is None:
            extra = {}

        body: dict[str, Any] = {
            k: v
            for k, v in {
                **extra,
                "username": username,
                "fullname": fullname,
                "authorized_sites": authorized_sites,
                "contactgroups": contactgroups,
                "auth_option": auth_option,
                "roles": roles,
                "customer": customer,
                "idle_timeout": idle_timeout,
                "interface_options": interface_options,
                "disable_notifications": disable_notifications,
                "disable_login": disable_login,
                "pager_address": pager_address,
                "language": language,
                "temperature_unit": temperature_unit,
                "contact_options": contact_options,
                "start_url": start_url,
            }.items()
            if v is not None
        }

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )

    def get(
        self,
        username: str | None = None,
        url: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        url_is_complete = False
        actual_url = ""

        if username is not None:
            url_is_complete = False
            actual_url = f"/objects/{self.domain}/{username}"

        elif url is not None:
            url_is_complete = True
            actual_url = url

        else:
            raise ValueError("Must specify username or url parameter")

        return self.request(
            "get",
            url=actual_url,
            url_is_complete=url_is_complete,
            expect_ok=expect_ok,
        )

    def get_all(self, effective_attributes: bool = False, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            query_params={"effective_attributes": "true" if effective_attributes else "false"},
            expect_ok=expect_ok,
        )

    def edit(
        self,
        username: str,
        fullname: str | None = None,
        customer: str = "provider",
        contactgroups: list[str] | None = None,
        authorized_sites: Sequence[str] | None = None,
        idle_timeout: dict[str, Any] | None = None,
        interface_options: dict[str, str] | None = None,
        auth_option: dict[str, Any] | None = None,
        disable_notifications: dict[str, bool] | None = None,
        disable_login: bool | None = None,
        contact_options: dict[str, Any] | None = None,
        pager_address: str | None = None,
        extra: dict[str, Any] | None = None,
        roles: list[str] | None = None,
        start_url: str | None = None,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        if extra is None:
            extra = {}

        body: dict[str, Any] = {
            k: v
            for k, v in {
                **extra,
                "fullname": fullname,
                "contactgroups": contactgroups,
                "authorized_sites": authorized_sites,
                "idle_timeout": idle_timeout,
                "customer": customer,
                "roles": roles,
                "interface_options": interface_options,
                "auth_option": auth_option,
                "disable_notifications": disable_notifications,
                "contact_options": contact_options,
                "disable_login": disable_login,
                "pager_address": pager_address,
                "start_url": start_url,
            }.items()
            if v is not None
        }

        return self.request(
            "put",
            url=f"/objects/{self.domain}/{username}",
            body=body,
            headers=self._set_etag_header(username, etag),
            expect_ok=expect_ok,
        )

    def delete(
        self,
        username: str,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{username}",
            expect_ok=expect_ok,
            headers=self._set_etag_header(username, etag),
        )

    def dismiss_warning(self, warning: DismissableWarning) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/dismiss-warning/invoke",
            body={"warning": warning},
        )

    def _set_etag_header(
        self, username: str, etag: IF_MATCH_HEADER_OPTIONS
    ) -> Mapping[str, str] | None:
        if etag == "valid_etag":
            return {"If-Match": self.get(username).headers["ETag"]}
        return set_if_match_header(etag)


class HostConfigClient(RestApiClient):
    domain: API_DOMAIN = "host_config"

    def get(
        self, host_name: str, effective_attributes: bool = False, expect_ok: bool = True
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/host_config/{host_name}",
            query_params={"effective_attributes": "true" if effective_attributes else "false"},
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        *,
        effective_attributes: bool | None = None,
        search: Mapping[str, object] | None = None,
        include_links: bool | None = None,
        fields: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            query_params=_only_set_keys(
                {
                    "effective_attributes": effective_attributes,
                    "include_links": include_links,
                    "fields": fields,
                    **(search or {}),
                }
            ),
            expect_ok=expect_ok,
        )

    def create(
        self,
        host_name: str,
        folder: str = "/",
        attributes: Mapping[str, Any] | Any | None = None,
        bake_agent: bool | None = None,
        expect_ok: bool = True,
    ) -> Response:
        if bake_agent is not None:
            query_params = {"bake_agent": "1" if bake_agent else "0"}
        else:
            query_params = {}
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            query_params=query_params,
            body={
                "host_name": host_name,
                "folder": folder,
                "attributes": attributes or {},
            },
            expect_ok=expect_ok,
        )

    def bulk_create(
        self,
        entries: list[dict[str, Any]],
        bake_agent: Literal["0", "1"] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        url = f"/domain-types/{self.domain}/actions/bulk-create/invoke"
        if bake_agent is not None:
            url += "?bake_agent=" + bake_agent

        return self.request(
            "post",
            url=url,
            body={"entries": entries},
            expect_ok=expect_ok,
        )

    def create_cluster(
        self,
        host_name: str,
        folder: str = "/",
        nodes: list[str] | None = None,
        attributes: Mapping[str, Any] | None = None,
        bake_agent: bool | None = None,
        expect_ok: bool = True,
    ) -> Response:
        if bake_agent is not None:
            query_params = {"bake_agent": "1" if bake_agent else "0"}
        else:
            query_params = {}
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/clusters",
            query_params=query_params,
            body={
                "host_name": host_name,
                "folder": folder,
                "nodes": nodes or [],
                "attributes": attributes or {},
            },
            expect_ok=expect_ok,
        )

    def edit(
        self,
        host_name: str,
        attributes: Mapping[str, Any] | None = None,
        update_attributes: Mapping[str, Any] | None = None,
        remove_attributes: Sequence[str] | None = None,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        body: dict[str, Any] = {}

        if attributes is not None:
            body["attributes"] = attributes

        if remove_attributes is not None:
            body["remove_attributes"] = remove_attributes

        if update_attributes is not None:
            body["update_attributes"] = update_attributes

        return self.request(
            "put",
            url=f"/objects/{self.domain}/" + host_name,
            body=body,
            expect_ok=expect_ok,
            headers=self._set_etag_header(host_name, etag),
        )

    def bulk_edit(
        self,
        entries: list[dict[str, Any]],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "put",
            url=f"/domain-types/{self.domain}/actions/bulk-update/invoke",
            body={"entries": entries},
            expect_ok=expect_ok,
        )

    def bulk_delete(
        self,
        entries: list[str],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/bulk-delete/invoke",
            body={"entries": entries},
            expect_ok=expect_ok,
        )

    def edit_property(
        self,
        host_name: str,
        property_name: str,
        property_value: Any,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{host_name}/properties/{property_name}",
            body=property_value,
            headers=self._set_etag_header(host_name, etag),
            expect_ok=expect_ok,
        )

    def delete(self, host_name: str, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{host_name}",
            expect_ok=expect_ok,
        )

    def move(
        self,
        host_name: str,
        target_folder: str,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{host_name}/actions/move/invoke",
            body={"target_folder": target_folder},
            expect_ok=expect_ok,
            headers=self._set_etag_header(host_name, etag),
        )

    def rename(
        self,
        host_name: str,
        new_name: str,
        expect_ok: bool = True,
        follow_redirects: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{host_name}/actions/rename/invoke",
            body={"new_name": new_name},
            expect_ok=expect_ok,
            follow_redirects=follow_redirects,
            headers=self._set_etag_header(host_name, etag),
        )

    def rename_wait_for_completion(
        self, expect_ok: bool = True, follow_redirects: bool = True
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/actions/wait-for-completion/invoke",
            expect_ok=expect_ok,
            follow_redirects=follow_redirects,
        )

    def _set_etag_header(
        self, host_name: str, etag: IF_MATCH_HEADER_OPTIONS
    ) -> Mapping[str, str] | None:
        if etag == "valid_etag":
            return {"If-Match": self.get(host_name=host_name).headers["ETag"]}
        return set_if_match_header(etag)


DELETE_MODE = Literal["recursive", "abort_on_nonempty"]


class FolderClient(RestApiClient):
    domain: API_DOMAIN = "folder_config"

    def get(self, folder_name: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{folder_name}",
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        *,
        parent: str | None = None,
        recursive: bool = False,
        show_hosts: bool = False,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            query_params=_only_set_keys(
                {
                    "parent": parent,
                    "recursive": recursive,
                    "show_hosts": show_hosts,
                }
            ),
            expect_ok=expect_ok,
        )

    def get_hosts(
        self,
        folder_name: str,
        *,
        effective_attributes: bool | None = None,
        include_links: bool | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{folder_name}/collections/hosts",
            expect_ok=expect_ok,
            query_params=_only_set_keys(
                {
                    "effective_attributes": effective_attributes,
                    "include_links": include_links,
                }
            ),
        )

    def create(
        self,
        title: str,
        parent: str,
        folder_name: str | None = None,
        attributes: Mapping[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body = {
            "title": title,
            "parent": parent,
            "attributes": attributes or {},
        }
        if folder_name is not None:
            body["name"] = folder_name

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )

    def bulk_edit(
        self,
        entries: list[dict[str, Any]],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "put",
            url=f"/domain-types/{self.domain}/actions/bulk-update/invoke",
            body={"entries": entries},
            expect_ok=expect_ok,
        )

    def edit(
        self,
        folder_name: str,
        title: str | None = None,
        attributes: Mapping[str, Any] | None = None,
        update_attributes: Mapping[str, Any] | None = None,
        remove_attributes: list[str] | None = None,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        body: dict[str, Any] = {"title": title} if title is not None else {}

        if attributes is not None:
            body["attributes"] = attributes

        if remove_attributes is not None:
            body["remove_attributes"] = remove_attributes

        if update_attributes is not None:
            body["update_attributes"] = update_attributes

        return self.request(
            "put",
            url=f"/objects/{self.domain}/{folder_name}",
            headers=self._set_etag_header(folder_name, etag),
            body=body,
            expect_ok=expect_ok,
        )

    def move(
        self,
        folder_name: str,
        destination: str,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{folder_name}/actions/move/invoke",
            body={"destination": destination},
            expect_ok=expect_ok,
            headers=self._set_etag_header(folder_name, etag),
        )

    def delete(
        self,
        folder_name: str,
        mode: DELETE_MODE | None = None,
        expect_ok: bool = True,
    ) -> Response:
        force_flag = f"?delete_mode={mode}" if mode is not None else ""

        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{folder_name}{force_flag}",
            expect_ok=expect_ok,
        )

    def _set_etag_header(
        self, folder_name: str, etag: IF_MATCH_HEADER_OPTIONS
    ) -> Mapping[str, str] | None:
        if etag == "valid_etag":
            return {"If-Match": self.get(folder_name=folder_name).headers["ETag"]}
        return set_if_match_header(etag)


class AuxTagClient(RestApiClient):
    domain: API_DOMAIN = "aux_tag"

    def get(self, aux_tag_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{aux_tag_id}",
            expect_ok=expect_ok,
        )

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def create(self, tag_data: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=tag_data,
            expect_ok=expect_ok,
        )

    def edit(
        self,
        aux_tag_id: str,
        tag_data: dict[str, Any],
        expect_ok: bool = True,
        with_etag: bool = True,
    ) -> Response:
        headers = None
        if with_etag:
            headers = {
                "If-Match": self.get(aux_tag_id).headers["ETag"],
                "Accept": "application/json",
            }
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{aux_tag_id}",
            body=tag_data,
            headers=headers,
            expect_ok=expect_ok,
        )

    def delete(self, aux_tag_id: str, expect_ok: bool = True) -> Response:
        etag = self.get(aux_tag_id).headers["ETag"]
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{aux_tag_id}/actions/delete/invoke",
            headers={"If-Match": etag, "Accept": "application/json"},
            expect_ok=expect_ok,
        )


class TimePeriodClient(RestApiClient):
    domain: API_DOMAIN = "time_period"

    def get(self, time_period_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{time_period_id}",
            expect_ok=expect_ok,
        )

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def delete(self, time_period_id: str, expect_ok: bool = True) -> Response:
        etag = self.get(time_period_id).headers["ETag"]
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{time_period_id}",
            headers={"If-Match": etag, "Accept": "application/json"},
            expect_ok=expect_ok,
        )

    def create(self, time_period_data: dict[str, object], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=time_period_data,
            expect_ok=expect_ok,
        )

    def edit(
        self,
        time_period_id: str,
        time_period_data: dict[str, object],
        expect_ok: bool = True,
    ) -> Response:
        etag = self.get(time_period_id).headers["ETag"]
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{time_period_id}",
            body=time_period_data,
            expect_ok=expect_ok,
            headers={"If-Match": etag, "Accept": "application/json"},
        )


class RuleClient(RestApiClient):
    domain: API_DOMAIN = "rule"

    def get(self, rule_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{rule_id}",
            expect_ok=expect_ok,
        )

    def list(self, ruleset: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
            query_params=_only_set_keys(
                {
                    "ruleset_name": ruleset,
                }
            ),
        )

    def delete(self, rule_id: str, expect_ok: bool = True) -> Response:
        etag = self.get(rule_id).headers["ETag"]
        resp = self.request(
            "delete",
            url=f"/objects/{self.domain}/{rule_id}",
            headers={"If-Match": etag, "Accept": "application/json"},
            expect_ok=expect_ok,
        )
        if expect_ok:
            resp.assert_status_code(204)
        return resp

    def create(
        self,
        ruleset: str,
        conditions: RuleConditions | None = None,
        folder: str = "~",
        value_raw: str | None = None,
        properties: RuleProperties | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body = _only_set_keys(
            {
                "ruleset": ruleset,
                "folder": folder,
                "properties": properties,
                "value_raw": value_raw,
                "conditions": conditions,
            }
        )

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )

    def move(self, rule_id: str, options: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{rule_id}/actions/move/invoke",
            body=options,
            expect_ok=expect_ok,
        )

    def edit(
        self,
        rule_id: str,
        value_raw: str | None = None,
        conditions: RuleConditions | None = None,
        properties: RuleProperties | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body = _only_set_keys(
            {
                "properties": properties if properties is not None else {},
                "value_raw": value_raw,
                "conditions": conditions,
            }
        )

        return self.request(
            "put",
            url=f"/objects/{self.domain}/{rule_id}",
            body=body,
            expect_ok=expect_ok,
        )


class RulesetClient(RestApiClient):
    domain: API_DOMAIN = "ruleset"

    def get(self, ruleset_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{ruleset_id}",
            expect_ok=expect_ok,
        )

    def list(
        self,
        *,
        fulltext: str | None = None,
        folder: str | None = None,
        deprecated: bool | None = None,
        used: bool | None = None,
        group: str | None = None,
        name: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
            query_params=_only_set_keys(
                {
                    "fulltext": fulltext,
                    "folder": folder,
                    "deprecated": deprecated,
                    "used": used,
                    "group": group,
                    "name": name,
                }
            ),
        )


class HostTagGroupClient(RestApiClient):
    domain: API_DOMAIN = "host_tag_group"

    def create(
        self,
        ident: str,
        title: str,
        tags: list[dict[str, str | list[str]]],
        topic: str | None = None,
        help_text: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body = {"id": ident, "title": title, "tags": tags}
        if help_text is not None:
            body["help"] = help_text
        if topic is not None:
            body["topic"] = topic

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )

    def get(self, ident: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{ident}",
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        *,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def delete(
        self,
        ident: str,
        repair: bool | None = None,
        mode: Literal["abort", "delete", "remove"] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        params: dict[str, Any] = {}
        if repair is not None:
            params["repair"] = repair
        if mode is not None:
            params["mode"] = mode
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{ident}",
            query_params=params,
            expect_ok=expect_ok,
        )

    def edit(
        self,
        ident: str,
        title: str | None = None,
        help_text: str | None = None,
        tags: list[dict[str, str]] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        etag = self.get(ident).headers["ETag"]
        body: dict[str, Any] = {"id": ident}
        if title is not None:
            body["title"] = title
        if help_text is not None:
            body["help"] = help_text
        if tags is not None:
            body["tags"] = tags
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{ident}",
            body=body,
            expect_ok=expect_ok,
            headers={"If-Match": etag, "Accept": "application/json"},
        )


class PasswordClient(RestApiClient):
    domain: API_DOMAIN = "password"

    def create(
        self,
        ident: str,
        title: str,
        password: str,
        shared: Sequence[str],
        editable_by: str | None = None,
        _owner: str | None = None,
        comment: str | None = None,
        customer: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=_only_set_keys(
                {
                    "ident": ident,
                    "title": title,
                    "password": password,
                    "shared": shared,
                    "editable_by": editable_by,
                    "owner": _owner,
                    "comment": comment,
                    "customer": "provider" if customer is None else customer,
                }
            ),
            expect_ok=expect_ok,
        )

    def get(self, ident: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{ident}",
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        *,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def edit(
        self,
        ident: str,
        title: str | None = None,
        comment: str | None = None,
        editable_by: str | None = None,
        password: str | None = None,
        shared: Sequence[str] | None = None,
        customer: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{ident}",
            body=_only_set_keys(
                {
                    "title": title,
                    "comment": comment,
                    "editable_by": editable_by,
                    "password": password,
                    "shared": shared,
                    "customer": customer,
                }
            ),
            expect_ok=expect_ok,
        )

    def delete(
        self,
        ident: str,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{ident}",
            expect_ok=expect_ok,
        )


class AgentClient(RestApiClient):
    domain: API_DOMAIN = "agent"

    def bake(self, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/bake/invoke",
            expect_ok=expect_ok,
        )

    def bake_status(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/actions/baking_status/invoke",
            expect_ok=expect_ok,
        )

    def bake_and_sign(self, key_id: int, passphrase: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/bake_and_sign/invoke",
            body={"key_id": key_id, "passphrase": passphrase},
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        *,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )


class DowntimeClient(RestApiClient):
    domain: API_DOMAIN = "downtime"

    def get(self, downtime_id: int, site_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{downtime_id}?site_id={site_id}",
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        *,
        host_name: str | None = None,
        service_description: str | None = None,
        query: str | None = None,
        downtime_type: Literal["host", "service", "both"] = "both",
        site_id: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
            query_params=_only_set_keys(
                {
                    "downtime_type": downtime_type,
                    "host_name": host_name,
                    "service_description": service_description,
                    "query": query,
                    "site_id": site_id,
                }
            ),
        )

    def create_for_host(
        self,
        start_time: datetime.datetime | str,
        end_time: datetime.datetime | str,
        recur: str | None = None,
        duration: int | None = None,
        comment: str | None = None,
        host_name: str | None = None,
        hostgroup_name: str | None = None,
        query: str | None = None,
        downtime_type: Literal["host", "hostgroup", "host_by_query"] = "host",
        expect_ok: bool = True,
    ) -> Response:
        body = {
            "downtime_type": downtime_type,
            "start_time": (start_time if isinstance(start_time, str) else start_time.isoformat()),
            "end_time": end_time if isinstance(end_time, str) else end_time.isoformat(),
            "recur": recur,
            "comment": comment,
            "duration": duration,
        }

        if downtime_type == "host":
            body.update({"host_name": host_name})

        elif downtime_type == "hostgroup":
            body.update({"hostgroup_name": hostgroup_name})

        else:
            body.update({"query": query})

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/host",
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    def create_for_services(
        self,
        start_time: datetime.datetime | str,
        end_time: datetime.datetime | str,
        recur: str | None = None,
        duration: int | None = None,
        comment: str | None = None,
        host_name: str | None = None,
        servicegroup_name: str | None = None,
        query: str | None = None,
        service_descriptions: list[str] | None = None,
        downtime_type: Literal["service", "servicegroup", "service_by_query"] = "service",
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {
            "downtime_type": downtime_type,
            "start_time": (start_time if isinstance(start_time, str) else start_time.isoformat()),
            "end_time": end_time if isinstance(end_time, str) else end_time.isoformat(),
            "recur": recur,
            "duration": duration,
            "comment": comment,
            "host_name": host_name,
        }

        if downtime_type == "service":
            body.update({"host_name": host_name, "service_descriptions": service_descriptions})

        elif downtime_type == "servicegroup":
            body.update({"servicegroup_name": servicegroup_name})

        else:
            body.update({"query": query})

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/service",
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    def delete(
        self,
        delete_type: FindByType,
        site_id: str | None = None,
        downtime_id: str | None = None,
        query: str | None = None,
        host_name: str | None = None,
        host_group: str | None = None,
        service_group: str | None = None,
        service_descriptions: list[str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {
            "delete_type": delete_type,
        }
        self._update_find_by_type(
            body,
            delete_type,
            site_id,
            downtime_id,
            query,
            host_name,
            host_group,
            service_group,
            service_descriptions,
        )

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    def modify(
        self,
        modify_type: FindByType,
        site_id: str | None = None,
        downtime_id: str | None = None,
        query: str | None = None,
        host_name: str | None = None,
        host_group: str | None = None,
        service_group: str | None = None,
        service_descriptions: list[str] | None = None,
        comment: str | None = None,
        end_time: str | int | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {
            "modify_type": modify_type,
            "comment": comment,
        }
        self._update_find_by_type(
            body,
            modify_type,
            site_id,
            downtime_id,
            query,
            host_name,
            host_group,
            service_group,
            service_descriptions,
        )

        if end_time is not None:
            body["end_time"] = {
                "value": end_time,
                "modify_type": "relative" if isinstance(end_time, int) else "absolute",
            }

        return self.request(
            "put",
            url=f"/domain-types/{self.domain}/actions/modify/invoke",
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    @staticmethod
    def _update_find_by_type(
        body: dict,
        find_type: FindByType,
        site_id: str | None = None,
        downtime_id: str | None = None,
        query: str | None = None,
        host_name: str | None = None,
        host_group: str | None = None,
        service_group: str | None = None,
        service_descriptions: list[str] | None = None,
    ) -> None:
        if find_type == "by_id":
            body.update({"downtime_id": downtime_id, "site_id": site_id})

        elif find_type == "query":
            body.update({"query": query})

        elif find_type == "hostgroup":
            body.update({"hostgroup_name": host_group})

        elif find_type == "servicegroup":
            body.update({"servicegroup_name": service_group})

        else:
            body.update({"host_name": host_name, "service_descriptions": service_descriptions})


class GroupConfig(RestApiClient):
    domain: API_DOMAIN

    def get(self, group_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{group_id}",
            expect_ok=expect_ok,
        )

    def bulk_create(self, groups: tuple[dict[str, str], ...], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            f"/domain-types/{self.domain}/actions/bulk-create/invoke",
            body={"entries": groups},
            expect_ok=expect_ok,
        )

    def list(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def bulk_edit(self, groups: tuple[dict[str, str], ...], expect_ok: bool = True) -> Response:
        return self.request(
            "put",
            f"/domain-types/{self.domain}/actions/bulk-update/invoke",
            body={"entries": groups},
            expect_ok=expect_ok,
        )

    def create(
        self,
        name: str,
        alias: str,
        customer: str = "provider",
        inventory_paths: APIInventoryPaths | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {"name": name, "alias": alias}
        if inventory_paths:
            body["inventory_paths"] = inventory_paths
        if version.edition(paths.omd_root) is version.Edition.CME:
            body["customer"] = customer

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )


class HostGroupClient(GroupConfig):
    domain: Literal["host_group_config"] = "host_group_config"


class ServiceGroupClient(GroupConfig):
    domain: Literal["service_group_config"] = "service_group_config"


class ContactGroupClient(GroupConfig):
    domain: Literal["contact_group_config"] = "contact_group_config"


class SiteManagementClient(RestApiClient):
    domain: API_DOMAIN = "site_connection"

    def get(self, site_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{site_id}",
            expect_ok=expect_ok,
        )

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def login(self, site_id: str, username: str, password: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{site_id}/actions/login/invoke",
            body={"username": username, "password": password},
            expect_ok=expect_ok,
        )

    def logout(self, site_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{site_id}/actions/logout/invoke",
            expect_ok=expect_ok,
        )

    def create(self, site_config: SiteConfig, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body={"site_config": site_config},
            expect_ok=expect_ok,
        )

    def update(self, site_id: str, site_config: SiteConfig, expect_ok: bool = True) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{site_id}",
            body={"site_config": site_config},
            expect_ok=expect_ok,
        )

    def delete(self, site_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{site_id}/actions/delete/invoke",
            expect_ok=expect_ok,
        )


class HostClient(RestApiClient):
    domain: Literal["host"] = "host"

    def get(self, host_name: str, columns: Sequence[str], expect_ok: bool = True) -> Response:
        url = f"/objects/host/{host_name}"
        if columns:
            url = f"{url}?{'&'.join(f'columns={c}' for c in columns)}"

        return self.request(
            "get",
            url=url,
            expect_ok=expect_ok,
        )

    # TODO: DEPRECATED(17003) - remove in 2.5
    def get_all(
        self,
        query: dict[str, Any],
        columns: Sequence[str] = ("name",),
        expect_ok: bool = True,
    ) -> Response:
        params = {"query": json.dumps(query), "columns": columns}
        return self.request(
            "get",
            url="/domain-types/host/collections/all",
            query_params=params,
            expect_ok=expect_ok,
        )

    def list_all(
        self,
        query: dict[str, Any],
        columns: Sequence[str] = ("name",),
        expect_ok: bool = True,
    ) -> Response:
        params = {"query": query, "columns": columns}
        return self.request(
            "post",
            url="/domain-types/host/collections/all",
            body=params,
            expect_ok=expect_ok,
        )

    def get_service(
        self,
        host_name: str,
        service_description: str,
        *,
        columns: Sequence[str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/host/{host_name}/actions/show_service/invoke",
            expect_ok=expect_ok,
            query_params=_only_set_keys(
                {
                    "service_description": service_description,
                    "columns": columns,
                }
            ),
        )

    def get_all_services(
        self,
        host_name: str,
        *,
        query: dict[str, object] | None = None,
        columns: Sequence[str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{host_name}/collections/services",
            expect_ok=expect_ok,
            body=_only_set_keys(
                {
                    "query": query,
                    "columns": columns,
                }
            ),
        )


class RuleNotificationClient(RestApiClient):
    domain: API_DOMAIN = "notification_rule"

    def get(self, rule_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{rule_id}",
            expect_ok=expect_ok,
        )

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def create(self, rule_config: APINotificationRule, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body={"rule_config": rule_config},
            expect_ok=expect_ok,
        )

    def edit(
        self, rule_id: str, rule_config: APINotificationRule, expect_ok: bool = True
    ) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{rule_id}",
            body={"rule_config": rule_config},
            expect_ok=expect_ok,
        )

    def delete(self, rule_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{rule_id}/actions/delete/invoke",
            expect_ok=expect_ok,
        )


class EventConsoleClient(RestApiClient):
    domain: API_DOMAIN = "event_console"

    def get(
        self,
        event_id: str,
        site_id: str,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{event_id}?site_id={site_id}",
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        *,
        query: str | None = None,
        host: str | None = None,
        application: str | None = None,
        state: Literal["warning", "ok", "critical", "unknown"] | None = None,
        phase: Literal["open", "ack"] | None = None,
        site_id: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
            query_params=_only_set_keys(
                {
                    "query": query,
                    "host": host,
                    "application": application,
                    "state": state,
                    "phase": phase,
                    "site_id": site_id,
                }
            ),
        )

    def update_and_acknowledge(
        self,
        event_id: str,
        site_id: str | None = None,
        change_comment: str | None = None,
        change_contact: str | None = None,
        expect_ok: bool = True,
        phase: Literal["open", "ack"] | None = None,
    ) -> Response:
        body = {
            "change_comment": change_comment,
            "change_contact": change_contact,
            "phase": phase,
        }

        if site_id is not None:
            body.update({"site_id": site_id})

        return self.request(
            "post",
            url=f"/objects/{self.domain}/{event_id}/actions/update_and_acknowledge/invoke",
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    def update_and_acknowledge_multiple(
        self,
        filter_type: Literal["query", "params", "all"],
        site_id: str | None = None,
        phase: Literal["open", "ack"] | None = None,
        change_comment: str | None = None,
        change_contact: str | None = None,
        query: str | None = None,
        host: str | None = None,
        application: str | None = None,
        state: Literal["warning", "ok", "critical", "unknown"] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {
            "site_id": site_id,
            "filter_type": filter_type,
            "change_comment": change_comment,
            "change_contact": change_contact,
            "phase": phase,
        }

        if filter_type == "query":
            body.update({"query": query})
        elif filter_type == "params":
            filters = {"state": state, "host": host, "application": application}
            body.update({"filters": {k: v for k, v in filters.items() if v is not None}})

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/update_and_acknowledge/invoke",
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    def change_event_state(
        self,
        event_id: str,
        site_id: str | None = None,
        new_state: Literal["warning", "ok", "critical", "unknown"] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {
            "new_state": new_state,
            "site_id": site_id,
        }

        return self.request(
            "post",
            url=f"/objects/{self.domain}/{event_id}/actions/change_state/invoke",
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    def change_multiple_event_states(
        self,
        filter_type: Literal["query", "params"],
        new_state: Literal["warning", "ok", "critical", "unknown"],
        site_id: str | None = None,
        query: str | None = None,
        host: str | None = None,
        application: str | None = None,
        state: Literal["warning", "ok", "critical", "unknown"] | None = None,
        phase: Literal["open", "ack"] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {
            "site_id": site_id,
            "filter_type": filter_type,
            "new_state": new_state,
        }

        if filter_type == "query":
            body.update({"query": query})
        else:
            filters = {
                "state": state,
                "host": host,
                "application": application,
                "phase": phase,
            }
            body.update({"filters": {k: v for k, v in filters.items() if v is not None}})

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/change_state/invoke",
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    def delete(
        self,
        filter_type: Literal["by_id", "query", "params"],
        site_id: str | None = None,
        query: str | None = None,
        event_id: int | None = None,
        host: str | None = None,
        application: str | None = None,
        state: Literal["warning", "ok", "critical", "unknown"] | None = None,
        phase: Literal["open", "ack"] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {"filter_type": filter_type}

        if site_id is not None:
            body.update({"site_id": site_id})

        if filter_type == "by_id":
            body.update({"event_id": event_id})

        elif filter_type == "query":
            body.update({"query": query})

        else:
            filters = {
                "state": state,
                "host": host,
                "application": application,
                "phase": phase,
            }
            body.update({"filters": {k: v for k, v in filters.items() if v is not None}})

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body=body,
            expect_ok=expect_ok,
        )


class CommentClient(RestApiClient):
    domain: API_DOMAIN = "comment"

    def delete(
        self,
        delete_type: str,
        site_id: str | None = None,
        comment_id: Any | None = None,
        host_name: str | None = None,
        service_descriptions: Sequence[str] | None = None,
        query: Mapping[str, str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body = _only_set_keys(
            {
                "site_id": site_id,
                "delete_type": delete_type,
                "comment_id": comment_id,
                "host_name": host_name,
                "service_descriptions": service_descriptions,
                "query": query,
            }
        )

        res = self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body=body,
            expect_ok=expect_ok,
        )

        if expect_ok:
            res.assert_status_code(204)

        return res

    def create_for_host(
        self,
        comment: str,
        comment_type: str = "host",
        host_name: str | None = None,
        query: Mapping[str, Any] | str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = _only_set_keys(
            {
                "comment": comment,
                "comment_type": comment_type,
                "host_name": host_name,
                "query": query,
            }
        )

        return self._create(body, "host", expect_ok)

    def create_for_service(
        self,
        comment: str,
        comment_type: str = "service",
        host_name: str | None = None,
        query: Mapping[str, Any] | str | None = None,
        service_description: str | None = None,
        persistent: bool | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = _only_set_keys(
            {
                "comment_type": comment_type,
                "comment": comment,
                "host_name": host_name,
                "query": query,
                "persistent": persistent,
                "service_description": service_description,
            }
        )

        return self._create(body, "service", expect_ok)

    def _create(self, body: dict[str, Any], collection: str, expect_ok: bool) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/{collection}",
            body=body,
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        *,
        host_name: str | None = None,
        service_description: str | None = None,
        query: Mapping[str, Any] | str | None = None,
        site_id: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        q: Mapping[str, Any] = _only_set_keys(
            {
                "host_name": host_name,
                "service_description": service_description,
                "query": query,
                "site_id": site_id,
            }
        )

        return self._get("all", q, expect_ok)

    def get_host(
        self,
        host_name: str | None = None,
        service_description: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        query: Mapping[str, Any] = _only_set_keys(
            {"host_name": host_name, "service_description": service_description}
        )

        return self._get("host", query, expect_ok)

    def get_service(self, expect_ok: bool = True) -> Response:
        return self._get("service", None, expect_ok)

    def _get(
        self,
        collection: str,
        query: Mapping[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/{collection}",
            query_params=query if query else None,
            expect_ok=expect_ok,
        )

    def get(
        self, comment_id: str | int, site_id: str | None = None, expect_ok: bool = True
    ) -> Response:
        # TODO: Agregar el parámetro site_id: str
        qp = _only_set_keys({"site_id": site_id})
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{comment_id}",
            query_params=qp if qp else None,
            expect_ok=expect_ok,
        )


class DcdClient(RestApiClient):
    domain: Literal["dcd"] = "dcd"

    def get(self, dcd_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{dcd_id}",
            expect_ok=expect_ok,
        )

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def create(
        self,
        dcd_id: str,
        site: str,
        title: (
            str | None
        ) = None,  # Set as optional in order to run tests on missing fields behavior
        comment: str | None = None,
        documentation_url: str | None = None,
        disabled: bool | None = None,
        interval: int | None = None,
        connector_type: str | None = None,
        discover_on_creation: bool | None = None,
        no_deletion_time_after_init: int | None = None,
        validity_period: int | None = None,
        creation_rules: list[dict[str, Any]] | None = None,
        restrict_source_hosts: list[str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = _only_set_keys(
            {
                "dcd_id": dcd_id,
                "title": title,
                "site": site,
                "comment": comment,
                "documentation_url": documentation_url,
                "disabled": disabled,
                "connector": _only_set_keys(
                    {
                        "connector_type": connector_type,
                        "interval": interval,
                        "discover_on_creation": discover_on_creation,
                        "no_deletion_time_after_init": no_deletion_time_after_init,
                        "validity_period": validity_period,
                        "creation_rules": creation_rules,
                        "restrict_source_hosts": restrict_source_hosts,
                    }
                ),
            }
        )

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )

    def edit(
        self,
        dcd_id: str,
        title: str,
        site: str,
        comment: str | None = None,
        documentation_url: str | None = None,
        disabled: bool | None = None,
        interval: int | None = None,
        discover_on_creation: bool | None = None,
        no_deletion_time_after_init: int | None = None,
        validity_period: int | None = None,
        creation_rules: list[dict[str, Any]] | None = None,
        exclude_time_ranges: list[dict[str, str]] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, Any] = {
            k: v
            for k, v in {
                "dcd_id": dcd_id,
                "title": title,
                "site": site,
                "comment": comment,
                "documentation_url": documentation_url,
                "disabled": disabled,
                "interval": interval,
                "discover_on_creation": discover_on_creation,
                "no_deletion_time_after_init": no_deletion_time_after_init,
                "validity_period": validity_period,
                "creation_rules": creation_rules,
                "exclude_time_ranges": exclude_time_ranges,
            }.items()
            if v is not None
        }

        return self.request(
            "put",
            url=f"/objects/{self.domain}/{dcd_id}",
            body=body,
            expect_ok=expect_ok,
        )

    def delete(self, dcd_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{dcd_id}",
            expect_ok=expect_ok,
        )


class AuditLogClient(RestApiClient):
    domain: API_DOMAIN = "audit_log"

    def get_all(
        self,
        date: Any = "now",
        object_type: str | None = None,
        object_id: str | None = None,
        user_id: str | None = None,
        regexp: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        query = _only_set_keys(
            {
                "date": date,
                "object_type": object_type,
                "object_id": object_id,
                "user_id": user_id,
                "regexp": regexp,
            },
        )

        result = self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            query_params=query,
            expect_ok=expect_ok,
        )

        if expect_ok:
            result.assert_status_code(200)

        return result

    def archive(self, expect_ok: bool = True) -> Response:
        result = self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/archive/invoke",
            expect_ok=expect_ok,
        )

        if expect_ok:
            result.assert_status_code(204)

        return result


class BiPackClient(RestApiClient):
    domain: API_DOMAIN = "bi_pack"

    def get(self, pack_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{pack_id}",
            expect_ok=expect_ok,
        )

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def create(self, pack_id: str, body: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{pack_id}",
            body=body,
            expect_ok=expect_ok,
        )

    def edit(self, pack_id: str, body: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{pack_id}",
            body=body,
            expect_ok=expect_ok,
        )

    def delete(self, pack_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{pack_id}",
            expect_ok=expect_ok,
        )


class BiAggregationClient(RestApiClient):
    domain: API_DOMAIN = "bi_aggregation"

    def get(self, aggregation_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{aggregation_id}",
            expect_ok=expect_ok,
        )

    def create(self, aggregation_id: str, body: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{aggregation_id}",
            body=body,
            expect_ok=expect_ok,
        )

    def edit(self, aggregation_id: str, body: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{aggregation_id}",
            body=body,
            expect_ok=expect_ok,
        )

    def delete(self, aggregation_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{aggregation_id}",
            expect_ok=expect_ok,
        )

    def get_aggregation_state_post(
        self,
        body: dict[str, Any],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/aggregation_state/invoke",
            body=body,
            expect_ok=expect_ok,
        )

    def get_aggregation_state(
        self,
        query_params: dict[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        url = f"/domain-types/{self.domain}/actions/aggregation_state/invoke"
        if query_params is not None:
            url += f"?{urllib.parse.urlencode(_only_set_keys(query_params))}"

        return self.request(
            "get",
            url=url,
            expect_ok=expect_ok,
        )


class BiRuleClient(RestApiClient):
    domain: API_DOMAIN = "bi_rule"

    def get(self, rule_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{rule_id}",
            expect_ok=expect_ok,
        )

    def create(self, rule_id: str, body: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{rule_id}",
            body=body,
            expect_ok=expect_ok,
        )

    def edit(self, rule_id: str, body: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{rule_id}",
            body=body,
            expect_ok=expect_ok,
        )

    def delete(self, rule_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{rule_id}",
            expect_ok=expect_ok,
        )


class UserRoleClient(RestApiClient):
    domain: API_DOMAIN = "user_role"

    def get(self, role_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{role_id}",
            expect_ok=expect_ok,
        )

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def clone(self, body: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )

    def edit(self, role_id: str, body: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{role_id}",
            body=body,
            expect_ok=expect_ok,
        )

    def delete(self, role_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{role_id}",
            expect_ok=expect_ok,
        )


class AutocompleteClient(RestApiClient):
    domain: API_DOMAIN = "autocomplete"

    def invoke(
        self,
        autocomplete_id: str,
        parameters: dict[str, Any],
        value: str = "",
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{autocomplete_id}",
            body={"value": value, "parameters": parameters},
            expect_ok=expect_ok,
        )


class SAMLConnectionClient(RestApiClient):
    domain: API_DOMAIN = "saml_connection"

    def get(self, saml_connection_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{saml_connection_id}",
            expect_ok=expect_ok,
        )

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def create(
        self,
        saml_data: dict[str, Any],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=saml_data,
            expect_ok=expect_ok,
        )

    def delete(
        self,
        saml_connection_id: str,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{saml_connection_id}",
            expect_ok=expect_ok,
            headers=self._set_etag_header(saml_connection_id, etag),
        )

    def _set_etag_header(
        self,
        saml_connection_id: str,
        etag: IF_MATCH_HEADER_OPTIONS,
    ) -> Mapping[str, str] | None:
        if etag == "valid_etag":
            return {"If-Match": self.get(saml_connection_id).headers["ETag"]}
        return set_if_match_header(etag)


class ServiceClient(RestApiClient):
    domain: API_DOMAIN = "service"

    def get_all(
        self,
        *,
        query: dict[str, object] | None = None,
        columns: Sequence[str] | None = None,
        host_name: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
            body=_only_set_keys(
                {
                    "query": query,
                    "columns": columns,
                    "host_name": host_name,
                }
            ),
        )


class ServiceDiscoveryClient(RestApiClient):
    service_discovery_domain: API_DOMAIN = "service_discovery"
    discovery_run_domain: API_DOMAIN = "discovery_run"

    def bulk_discovery(
        self,
        hostnames: Sequence[str],
        monitor_undecided_services: bool = False,
        remove_vanished_services: bool = False,
        update_service_labels: bool = False,
        update_host_labels: bool = False,
        do_full_scan: bool | None = None,
        bulk_size: int | None = None,
        ignore_errors: bool | None = None,
        follow_redirects: bool = True,
        expect_ok: bool = True,
    ) -> Response:
        body: dict = {
            "hostnames": hostnames,
            "options": {
                "monitor_undecided_services": monitor_undecided_services,
                "remove_vanished_services": remove_vanished_services,
                "update_service_labels": update_service_labels,
                "update_host_labels": update_host_labels,
            },
        }

        if do_full_scan is not None:
            body["do_full_scan"] = do_full_scan
        if bulk_size is not None:
            body["bulk_size"] = bulk_size
        if ignore_errors is not None:
            body["ignore_errors"] = ignore_errors

        return self.request(
            "post",
            url=f"/domain-types/{self.discovery_run_domain}/actions/bulk-discovery-start/invoke",
            body=body,
            expect_ok=expect_ok,
            follow_redirects=follow_redirects,
        )

    def discovery_run_status(self, id_: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.discovery_run_domain}/{id_}",
            expect_ok=expect_ok,
        )


class LDAPConnectionClient(RestApiClient):
    domain: API_DOMAIN = "ldap_connection"

    def get(
        self,
        ldap_connection_id: str,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{ldap_connection_id}",
            expect_ok=expect_ok,
        )

    def get_all(
        self,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def create(
        self,
        ldap_data: dict[str, Any],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=ldap_data,
            expect_ok=expect_ok,
        )

    def delete(
        self,
        ldap_connection_id: str,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{ldap_connection_id}",
            expect_ok=expect_ok,
            headers=self._set_etag_header(ldap_connection_id, etag),
        )

    def edit(
        self,
        ldap_connection_id: str,
        ldap_data: dict[str, Any],
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{ldap_connection_id}",
            body=ldap_data,
            expect_ok=expect_ok,
            headers=self._set_etag_header(ldap_connection_id, etag),
        )

    def _set_etag_header(
        self,
        ldap_connection_id: str,
        etag: IF_MATCH_HEADER_OPTIONS,
    ) -> Mapping[str, str] | None:
        if etag == "valid_etag":
            return {"If-Match": self.get(ldap_connection_id).headers["ETag"]}
        return set_if_match_header(etag)


class ParentScanClient(RestApiClient):
    domain: API_DOMAIN = "parent_scan"

    def start(
        self,
        host_names: Sequence[str],
        gateway_hosts: Any,
        performance_settings: dict | None = None,
        force_explicit_parents: bool | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body = {
            "host_names": host_names,
            "gateway_hosts": gateway_hosts,
            "configuration": {},
            "performance": {},
        }
        if force_explicit_parents is not None:
            body["configuration"]["force_explicit_parents"] = force_explicit_parents

        if performance_settings:
            body["performance"] = performance_settings

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/start/invoke",
            body=body,
        )


class QuickSetupClient(RestApiClient):
    domain: API_DOMAIN = "quick_setup"
    domain_stage: API_DOMAIN = "quick_setup_stage"

    def get_overview_mode_or_guided_mode(
        self,
        quick_setup_id: str,
        mode: Literal["overview", "guided"] | None = "guided",
        object_id: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{quick_setup_id}",
            query_params=_only_set_keys({"mode": mode, "object_id": object_id}),
            expect_ok=expect_ok,
        )

    def run_stage_action(
        self,
        quick_setup_id: str,
        stage_action_id: str,
        stages: list[dict[str, Any]],
        follow_redirects: bool = True,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{quick_setup_id}/actions/run-stage-action/invoke",
            body={
                "stages": stages,
                "stage_action_id": stage_action_id,
            },
            follow_redirects=follow_redirects,
            expect_ok=expect_ok,
        )

    def get_stage_structure(
        self,
        quick_setup_id: str,
        stage_index: int,
        object_id: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{quick_setup_id}/quick_setup_stage/{stage_index}",
            query_params=_only_set_keys(
                {
                    "object_id": object_id,
                }
            ),
            expect_ok=expect_ok,
        )

    def run_quick_setup_action(
        self,
        quick_setup_id: str,
        payload: dict[str, Any],
        follow_redirects: bool = True,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/objects/{self.domain}/{quick_setup_id}/actions/run-action/invoke",
            body=payload,
            follow_redirects=follow_redirects,
            expect_ok=expect_ok,
        )

    def edit_quick_setup(
        self,
        quick_setup_id: str,
        payload: dict[str, Any],
        object_id: str,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{quick_setup_id}/actions/edit/invoke",
            body=payload,
            query_params={"object_id": object_id},
            expect_ok=expect_ok,
        )


class ConfigurationEntityClient(RestApiClient):
    domain: API_DOMAIN = "configuration_entity"

    def create_configuration_entity(
        self,
        payload: dict[str, Any],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=payload,
            expect_ok=expect_ok,
        )

    def update_configuration_entity(
        self,
        payload: dict[str, Any],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "put",
            url=f"/domain-types/{self.domain}/actions/edit-single-entity/invoke",
            body=payload,
            expect_ok=expect_ok,
        )

    def list_configuration_entities(
        self,
        entity_type: ConfigEntityType,
        entity_type_specifier: str,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{to_domain_type(entity_type)}/collections/{entity_type_specifier}",
            expect_ok=expect_ok,
        )

    def get_configuration_entity(
        self,
        entity_type: ConfigEntityType,
        entity_id: str,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/{to_domain_type(entity_type)}/{entity_id}",
            expect_ok=expect_ok,
        )

    def get_configuration_entity_schema(
        self,
        entity_type: ConfigEntityType,
        entity_type_specifier: str,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/form_spec/collections/{to_domain_type(entity_type)}?entity_type_specifier={entity_type_specifier}",
            expect_ok=expect_ok,
        )


class ManagedRobotsClient(RestApiClient):
    domain: API_DOMAIN = "managed_robots"

    def show(self, robot_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{robot_id}",
            expect_ok=expect_ok,
        )

    def delete(self, robot_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{robot_id}",
            expect_ok=expect_ok,
        )

    def create(self, managed_robot_data: dict[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=managed_robot_data,
            expect_ok=expect_ok,
        )


class BrokerConnectionClient(RestApiClient):
    domain: API_DOMAIN = "broker_connection"

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )

    def get(self, connection_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{connection_id}",
            expect_ok=expect_ok,
        )

    def create(
        self,
        payload: dict[str, Any],
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=payload,
            expect_ok=expect_ok,
        )

    def edit(
        self,
        connection_id: str,
        payload: dict[str, Any],
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{connection_id}",
            body=payload,
            expect_ok=expect_ok,
            headers=self._set_etag_header(connection_id, etag),
        )

    def delete(
        self,
        connection_id: str,
        expect_ok: bool = True,
        etag: IF_MATCH_HEADER_OPTIONS = "star",
    ) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{connection_id}",
            expect_ok=expect_ok,
            headers=self._set_etag_header(connection_id, etag),
        )

    def _set_etag_header(
        self,
        connection_id: str,
        etag: IF_MATCH_HEADER_OPTIONS,
    ) -> Mapping[str, str] | None:
        if etag == "valid_etag":
            return {"If-Match": self.get(connection_id).headers["ETag"]}
        return set_if_match_header(etag)


class OtelConfigClient(RestApiClient):
    domain: API_DOMAIN = "otel_collector_config"

    def get_all(self, expect_ok: bool = True) -> Response:
        return self.request(
            "get", url=f"/domain-types/{self.domain}/collections/all", expect_ok=expect_ok
        )

    def create(self, payload: Mapping[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=dict(payload),
            expect_ok=expect_ok,
        )

    def edit(self, config_id: str, payload: Mapping[str, Any], expect_ok: bool = True) -> Response:
        return self.request(
            "put",
            url=f"/objects/{self.domain}/{config_id}",
            body=dict(payload),
            expect_ok=expect_ok,
        )

    def delete(self, config_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{config_id}",
            expect_ok=expect_ok,
        )


class BackgroundJobClient(RestApiClient):
    domain: API_DOMAIN = "background_job"

    def get(self, job_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{job_id}",
            expect_ok=expect_ok,
        )


class AcknowledgeClient(RestApiClient):
    domain: API_DOMAIN = "acknowledge"

    def remove_for_host(self, host_name: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body={"acknowledge_type": "host", "host_name": host_name},
            expect_ok=expect_ok,
        )

    def remove_for_host_group(self, host_group_name: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body={"acknowledge_type": "hostgroup", "hostgroup_name": host_group_name},
            expect_ok=expect_ok,
        )

    def remove_for_host_by_query(
        self, query: dict[str, object], expect_ok: bool = True
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body={"acknowledge_type": "host_by_query", "query": query},
            expect_ok=expect_ok,
        )

    def remove_for_service(
        self, host_name: str, service_description: str, expect_ok: bool = True
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body={
                "acknowledge_type": "service",
                "host_name": host_name,
                "service_description": service_description,
            },
            expect_ok=expect_ok,
        )

    def remove_for_service_group(self, service_group_name: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body={"acknowledge_type": "servicegroup", "servicegroup_name": service_group_name},
            expect_ok=expect_ok,
        )

    def remove_for_service_by_query(
        self, query: dict[str, object], expect_ok: bool = True
    ) -> Response:
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/actions/delete/invoke",
            body={"acknowledge_type": "service_by_query", "query": query},
            expect_ok=expect_ok,
        )


@dataclasses.dataclass
class ClientRegistry:
    """Overall client registry for all available endpoint family clients.

    Guidelines for individual clients:
        1) Keep in mind that this is a test client rather than a user client.
        This implies that not all fields must be made available as function arguments. This
        applies especially to nested fields where a top-level dict definition should be enough.
        Take a look at the 'performance_settings' of the ParentScan.start method.

    """

    ConfigurationEntity: ConfigurationEntityClient
    Licensing: LicensingClient
    ActivateChanges: ActivateChangesClient
    User: UserClient
    HostConfig: HostConfigClient
    Host: HostClient
    Folder: FolderClient
    AuxTag: AuxTagClient
    TimePeriod: TimePeriodClient
    Rule: RuleClient
    Ruleset: RulesetClient
    HostTagGroup: HostTagGroupClient
    Password: PasswordClient
    Agent: AgentClient
    Downtime: DowntimeClient
    HostGroup: HostGroupClient
    ServiceGroup: ServiceGroupClient
    ContactGroup: ContactGroupClient
    SiteManagement: SiteManagementClient
    RuleNotification: RuleNotificationClient
    Comment: CommentClient
    EventConsole: EventConsoleClient
    Dcd: DcdClient
    AuditLog: AuditLogClient
    BiPack: BiPackClient
    BiAggregation: BiAggregationClient
    BiRule: BiRuleClient
    UserRole: UserRoleClient
    AutoComplete: AutocompleteClient
    Service: ServiceClient
    ServiceDiscovery: ServiceDiscoveryClient
    LdapConnection: LDAPConnectionClient
    SamlConnection: SAMLConnectionClient
    ParentScan: ParentScanClient
    QuickSetup: QuickSetupClient
    ManagedRobots: ManagedRobotsClient
    BrokerConnection: BrokerConnectionClient
    BackgroundJob: BackgroundJobClient
    Acknowledge: AcknowledgeClient
    OtelConfigClient: OtelConfigClient


def get_client_registry(request_handler: RequestHandler, url_prefix: str) -> ClientRegistry:
    return ClientRegistry(
        ConfigurationEntity=ConfigurationEntityClient(request_handler, url_prefix),
        Licensing=LicensingClient(request_handler, url_prefix),
        ActivateChanges=ActivateChangesClient(request_handler, url_prefix),
        User=UserClient(request_handler, url_prefix),
        HostConfig=HostConfigClient(request_handler, url_prefix),
        Host=HostClient(request_handler, url_prefix),
        Folder=FolderClient(request_handler, url_prefix),
        AuxTag=AuxTagClient(request_handler, url_prefix),
        TimePeriod=TimePeriodClient(request_handler, url_prefix),
        Rule=RuleClient(request_handler, url_prefix),
        Ruleset=RulesetClient(request_handler, url_prefix),
        HostTagGroup=HostTagGroupClient(request_handler, url_prefix),
        Password=PasswordClient(request_handler, url_prefix),
        Agent=AgentClient(request_handler, url_prefix),
        Downtime=DowntimeClient(request_handler, url_prefix),
        HostGroup=HostGroupClient(request_handler, url_prefix),
        ServiceGroup=ServiceGroupClient(request_handler, url_prefix),
        ContactGroup=ContactGroupClient(request_handler, url_prefix),
        SiteManagement=SiteManagementClient(request_handler, url_prefix),
        RuleNotification=RuleNotificationClient(request_handler, url_prefix),
        Comment=CommentClient(request_handler, url_prefix),
        EventConsole=EventConsoleClient(request_handler, url_prefix),
        Dcd=DcdClient(request_handler, url_prefix),
        AuditLog=AuditLogClient(request_handler, url_prefix),
        BiPack=BiPackClient(request_handler, url_prefix),
        BiAggregation=BiAggregationClient(request_handler, url_prefix),
        BiRule=BiRuleClient(request_handler, url_prefix),
        UserRole=UserRoleClient(request_handler, url_prefix),
        AutoComplete=AutocompleteClient(request_handler, url_prefix),
        Service=ServiceClient(request_handler, url_prefix),
        ServiceDiscovery=ServiceDiscoveryClient(request_handler, url_prefix),
        LdapConnection=LDAPConnectionClient(request_handler, url_prefix),
        ParentScan=ParentScanClient(request_handler, url_prefix),
        SamlConnection=SAMLConnectionClient(request_handler, url_prefix),
        QuickSetup=QuickSetupClient(request_handler, url_prefix),
        ManagedRobots=ManagedRobotsClient(request_handler, url_prefix),
        BrokerConnection=BrokerConnectionClient(request_handler, url_prefix),
        BackgroundJob=BackgroundJobClient(request_handler, url_prefix),
        Acknowledge=AcknowledgeClient(request_handler, url_prefix),
        OtelConfigClient=OtelConfigClient(request_handler, url_prefix),
    )
