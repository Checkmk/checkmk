#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import abc
import dataclasses
import json
import multiprocessing
import pprint
import queue
import urllib.parse
from collections.abc import Mapping
from typing import Any, cast, Literal, NoReturn, Sequence, TypedDict

from pydantic import BaseModel, StrictStr

from cmk.utils import version
from cmk.utils.type_defs import HTTPMethod

JSON = int | str | bool | list[Any] | dict[str, Any] | None
JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def _only_set_keys(body: dict[str, Any | None]) -> dict[str, Any]:
    return {k: v for k, v in body.items() if v is not None}


class Link(BaseModel):
    domainType: Literal["link"]
    rel: StrictStr
    href: StrictStr
    method: Literal["GET", "PUT", "DELETE"]
    type: Literal["application/json"]


class ObjectResponse(BaseModel):
    links: list[Link]
    members: dict


class CollectionResponse(BaseModel):
    links: list[Link]
    extensions: dict


@dataclasses.dataclass(frozen=True)
class Response:
    status_code: int
    body: bytes | None
    headers: Mapping[str, str]

    def assert_status_code(self, status_code: int) -> Response:
        assert self.status_code == status_code
        return self

    @property
    def json(self):
        assert self.body is not None  # mostly for mypy
        return json.loads(self.body.decode("utf-8"))


class RestApiException(Exception):
    def __init__(
        self, url: str, method: str, body: Any, headers: Mapping[str, str], response: Response
    ) -> None:
        super().__init__(url, method, body, headers, response)
        self.url = url
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
                    "body": self.body,
                    "headers": self.headers,
                },
                "response": {
                    "status": self.response.status_code,
                    "body": formatted_body,
                    "headers": self.response.headers,
                },
            }
        )


def get_link(resp: dict, rel: str) -> Mapping:
    for link in resp.get("links", []):
        if link["rel"].startswith(rel):
            return link
    if "result" in resp:
        for link in resp["result"].get("links", []):
            if link["rel"].startswith(rel):
                return link
    for member in resp.get("members", {}).values():
        if member["memberType"] == "action":
            for link in member["links"]:
                if link["rel"].startswith(rel):
                    return link
    raise KeyError("{!r} not found".format(rel))


def expand_rel(rel: str) -> str:
    if rel.startswith(".../"):
        rel = rel.replace(".../", "urn:org.restfulobjects:rels/")
    if rel.startswith("cmk/"):
        rel = rel.replace("cmk/", "urn:com.checkmk:rels/")
    return rel


class RequestHandler(abc.ABC):
    """A class representing a way to do HTTP Requests."""

    @abc.abstractmethod
    def set_credentials(self, username: str, password: str) -> None:
        ...

    @abc.abstractmethod
    def request(
        self,
        method: HTTPMethod,
        url: str,
        query_params: Mapping[str, str] | None = None,
        body: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        ...


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


class StringMatcher(TypedDict):
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


class RuleConditions(TypedDict, total=False):
    host_name: StringMatcher
    host_tags: list[HostTagMatcher]
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
        pydantic_basemodel_body: BaseModel | None = None,
        query_params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        expect_ok: bool = True,
        follow_redirects: bool = True,
        url_is_complete: bool = False,
        use_default_headers: bool = True,
    ) -> Response:
        if use_default_headers:
            default_headers = JSON_HEADERS.copy()
            default_headers.update(headers or {})
        else:
            default_headers = cast(
                dict[str, str], headers
            )  # TODO FIX this. Need this to test exceptions

        if not url_is_complete:
            url = self._url_prefix + url

        if pydantic_basemodel_body is not None:
            request_body = pydantic_basemodel_body.json()
        else:
            if body is not None:
                request_body = json.dumps(body)
            else:
                request_body = ""

        resp = self.request_handler.request(
            method=method,
            url=url,
            query_params=query_params,
            body=request_body,
            headers=default_headers,
        )

        if expect_ok and resp.status_code >= 400:
            raise RestApiException(url, method, body, default_headers, resp)
        if follow_redirects and 300 <= resp.status_code < 400:
            return self.request(
                method=method,
                url=resp.headers["Location"],
                query_params=query_params,
                body=body,
                headers=default_headers,
                url_is_complete=url_is_complete,
            )
        return resp

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

    def get_folder(self, folder_name: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/folder_config/{folder_name}",
            expect_ok=expect_ok,
        )

    def create_folder(
        self,
        folder_name: str,
        title: str,
        parent: str,
        attributes: Mapping[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        return self.request(
            "post",
            url="/domain-types/folder_config/collections/all",
            body={
                "name": folder_name,
                "title": title,
                "parent": parent,
                "attributes": attributes or {},
            },
            expect_ok=expect_ok,
        )

    def edit_folder(
        self,
        folder_name: str,
        title: str,
        attributes: Mapping[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        etag = self.get_folder(folder_name).headers["ETag"]
        headers = {"IF-Match": etag}
        body = {"title": title, "attributes": attributes}
        return self.request(
            "put",
            url=f"/objects/folder_config/{folder_name}",
            headers=headers,
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
        )

    def show_host(
        self, host_name: str, effective_attributes: bool = False, expect_ok: bool = True
    ) -> Response:
        return self.request(
            "get",
            url=f"/objects/host_config/{host_name}",
            query_params={"effective_attributes": "true" if effective_attributes else "false"},
        )

    def create_host(
        self,
        host_name: str,
        folder: str = "/",
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
            url="/domain-types/host_config/collections/all",
            query_params=query_params,
            body={"host_name": host_name, "folder": folder, "attributes": attributes or {}},
            expect_ok=expect_ok,
        )

    def bulk_create_hosts(self, *args: JSON, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url="/domain-types/host_config/actions/bulk-create/invoke",
            body={"entries": args},
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
            url="/domain-types/host_config/collections/clusters",
            query_params=query_params,
            body={
                "host_name": host_name,
                "folder": folder,
                "nodes": nodes or [],
                "attributes": attributes or {},
            },
            expect_ok=expect_ok,
        )

    def get_host(self, host_name: str, expect_ok: bool = True) -> Response:
        return self.request("get", url="/objects/host_config/" + host_name, expect_ok=expect_ok)

    def edit_host(
        self,
        host_name: str,
        folder: str | None = "/",
        attributes: Mapping[str, Any] | None = None,
        update_attributes: Mapping[str, Any] | None = None,
        remove_attributes: Sequence[str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        etag = self.get_host(host_name).headers["ETag"]
        headers = {"IF-Match": etag, "Accept": "application/json"}
        body = {
            "attributes": attributes,
            "update_attributes": update_attributes,
            "remove_attributes": remove_attributes,
        }
        return self.request(
            "put",
            url="/objects/host_config/" + host_name,
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
            headers=headers,
        )

    def bulk_edit_hosts(self, *args: JSON, expect_ok: bool = True) -> Response:
        return self.request(
            "put",
            url="/domain-types/host_config/actions/bulk-update/invoke",
            body={"entries": args},
            expect_ok=expect_ok,
        )

    def edit_host_property(
        self, host_name: str, property_name: str, property_value: Any, expect_ok: bool = True
    ) -> Response:
        etag = self.get_host(host_name).headers["ETag"]
        headers = {"IF-Match": etag}
        return self.request(
            "put",
            url=f"/objects/host_config/{host_name}/properties/{property_name}",
            body=property_value,
            headers=headers,
            expect_ok=expect_ok,
        )

    def delete_host(self, host_name: str) -> Response:
        return self.request("delete", url=f"/objects/host_config/{host_name}")

    def activate_changes(
        self,
        sites: list[str] | None = None,
        redirect: bool = False,
        force_foreign_changes: bool = False,
        expect_ok: bool = True,
    ) -> Response:
        if sites is None:
            sites = []
        return self.request(
            "post",
            url="/domain-types/activation_run/actions/activate-changes/invoke",
            body={
                "redirect": redirect,
                "sites": sites,
                "force_foreign_changes": force_foreign_changes,
            },
            expect_ok=expect_ok,
        )

    def call_activate_changes_and_wait_for_completion(
        self,
        sites: list[str] | None = None,
        force_foreign_changes: bool = False,
        timeout_seconds: int = 60,
    ) -> Response | NoReturn:
        if sites is None:
            sites = []
        response = self.request(
            "post",
            url="/domain-types/activation_run/actions/activate-changes/invoke",
            body={
                "redirect": True,
                "sites": sites,
                "force_foreign_changes": force_foreign_changes,
            },
            expect_ok=False,
            follow_redirects=False,
        )

        if response.status_code != 302:
            return response

        que: multiprocessing.Queue[Response] = multiprocessing.Queue()

        def waiter(result_que: multiprocessing.Queue, initial_response: Response) -> None:
            wait_response = initial_response
            while wait_response.status_code == 302:
                wait_response = self.request(
                    "get",
                    url=wait_response.headers["Location"],
                    expect_ok=False,
                    url_is_complete=True,
                )
            result_que.put(wait_response)

        p = multiprocessing.Process(target=waiter, args=(que, response))
        p.start()
        try:
            result = que.get(timeout=timeout_seconds)
        except queue.Empty:
            raise TimeoutError
        finally:
            p.kill()
            p.join()

        return result

    def call_online_verification(self, expect_ok: bool = False) -> Response:
        return self.request(
            "post",
            url="/domain-types/licensing/actions/verify/invoke",
            expect_ok=expect_ok,
        )

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
            "post", url="/domain-types/metric/actions/get/invoke", body=body, expect_ok=expect_ok
        )

    # TODO: add optional parameters
    def create_user(
        self,
        username: str,
        fullname: str,
        authorized_sites: Sequence[str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, str | Sequence[str]] = {
            "username": username,
            "fullname": fullname,
        }

        if authorized_sites is not None:
            body["authorized_sites"] = authorized_sites

        if version.is_managed_edition():
            body["customer"] = "provider"

        return self.request(
            "post",
            url="/domain-types/user_config/collections/all",
            body=body,
            expect_ok=expect_ok,
        )

    def list_rulesets(
        self,
        fulltext: str | None = None,
        folder: str | None = None,
        deprecated: bool | None = None,
        used: bool | None = None,
        group: str | None = None,
        name: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        query_params = urllib.parse.urlencode(
            _only_set_keys(
                {
                    "fulltext": fulltext,
                    "folder": folder,
                    "deprecated": deprecated,
                    "used": used,
                    "group": group,
                    "name": name,
                }
            )
        )

        return self.request(
            "get", url="/domain-types/ruleset/collections/all?" + query_params, expect_ok=expect_ok
        )

    def show_user(self, username: str, expect_ok: bool = True) -> Response:
        return self.request("get", url=f"/objects/user_config/{username}", expect_ok=expect_ok)

    # TODO: add additional parameters
    def edit_user(
        self,
        username: str,
        fullname: str | None = None,
        contactgroups: list[str] | None = None,
        authorized_sites: Sequence[str] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body: dict[str, str | Sequence[str] | None] = {
            "fullname": fullname,
            "contactgroups": contactgroups,
        }

        if authorized_sites is not None:
            body["authorized_sites"] = authorized_sites

        # if there is no object, there's probably no etag.
        # But we want the 404 from the request below!
        etag = self.show_user(username, expect_ok=expect_ok).headers.get("E-Tag")
        if etag is not None:
            headers = {"If-Match": etag}
        else:
            headers = {}

        return self.request(
            "put",
            url=f"/objects/user_config/{username}",
            body={k: v for k, v in body.items() if v is not None},
            headers=headers,
            expect_ok=expect_ok,
        )

    def bake_and_sign_agent(self, key_id: int, passphrase: str, expect_ok: bool = True) -> Response:
        return self.request(
            "post",
            url="/domain-types/agent/actions/bake_and_sign/invoke",
            body={"key_id": key_id, "passphrase": passphrase},
            expect_ok=expect_ok,
        )


class AuxTagTestClient(RestApiClient):
    domain: Literal["aux_tag"] = "aux_tag"

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


class TimePeriodObject(BaseModel):
    alias: StrictStr
    active_time_ranges: list
    exceptions: list
    exclude: list | None  # builtin timeperiods don't have an exclude field


class TimePeriodObjectResponse(ObjectResponse):
    domainType: Literal["time_period"]
    id: StrictStr
    title: StrictStr
    extensions: TimePeriodObject


class TimePeriodCollectionResponse(CollectionResponse):
    id: Literal["time_period"]
    domainType: Literal["time_period"]
    value: list[TimePeriodObjectResponse]


class TimePeriodTestClient(RestApiClient):
    domain: Literal["time_period"] = "time_period"

    def get(self, time_period_id: str, expect_ok: bool = True) -> Response:
        resp = self.request(
            "get",
            url=f"/objects/{self.domain}/{time_period_id}",
            expect_ok=expect_ok,
        )
        if expect_ok:
            TimePeriodObjectResponse(**resp.json)
        return resp

    def get_all(self, expect_ok: bool = True) -> Response:
        resp = self.request(
            "get",
            url=f"/domain-types/{self.domain}/collections/all",
            expect_ok=expect_ok,
        )
        if expect_ok:
            TimePeriodCollectionResponse(**resp.json)
        return resp

    def delete(self, time_period_id: str, expect_ok: bool = True) -> Response:
        etag = self.get(time_period_id).headers["ETag"]
        resp = self.request(
            "delete",
            url=f"/objects/{self.domain}/{time_period_id}",
            headers={"If-Match": etag, "Accept": "application/json"},
            expect_ok=expect_ok,
        )
        return resp

    def create(self, time_period_data: dict[str, object], expect_ok: bool = True) -> Response:
        resp = self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=time_period_data,
            expect_ok=expect_ok,
        )
        if expect_ok:
            TimePeriodObjectResponse(**resp.json)
        return resp

    def edit(
        self, time_period_id: str, time_period_data: dict[str, object], expect_ok: bool = True
    ) -> Response:
        etag = self.get(time_period_id).headers["ETag"]
        resp = self.request(
            "put",
            url=f"/objects/{self.domain}/{time_period_id}",
            body=time_period_data,
            expect_ok=expect_ok,
            headers={"If-Match": etag, "Accept": "application/json"},
        )

        return resp


# === Rules Endpoint Client ===


class RulesTestClient(RestApiClient):
    domain: Literal["rule"] = "rule"

    def get(self, rule_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{rule_id}",
            expect_ok=expect_ok,
        )

    def list_rules(self, ruleset: str, expect_ok: bool = True) -> Response:
        url = f"/domain-types/{self.domain}/collections/all"
        if ruleset:
            url = f"/domain-types/{self.domain}/collections/all?ruleset_name={ruleset}"

        return self.request(
            "get",
            url=url,
            expect_ok=expect_ok,
        )

    def delete(self, rule_id: str, expect_ok: bool = True) -> Response:
        etag = self.get(rule_id).headers["ETag"]
        resp = self.request(
            "delete",
            url=f"/objects/{self.domain}/{rule_id}",
            headers={"If-Match": etag, "Accept": "application/json"},
        )
        if expect_ok:
            resp.assert_status_code(204)
        return resp

    def create(
        self,
        ruleset: str,
        value_raw: str,
        conditions: RuleConditions,
        folder: str = "~",
        properties: RuleProperties | None = None,
        expect_ok: bool = False,
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
            url=f"/objects/rule/{rule_id}/actions/move/invoke",
            body=options,
            expect_ok=expect_ok,
        )


# === Rulesets Endpoint Client ===


class RulesetTestClient(RestApiClient):
    domain: Literal["ruleset"] = "ruleset"

    def get_all(self, search_options: str | None = None, expect_ok: bool = True) -> Response:
        url = f"/domain-types/{self.domain}/collections/all"
        if search_options is not None:
            url = f"/domain-types/{self.domain}/collections/all{search_options}"

        return self.request("get", url=url, expect_ok=expect_ok)

    def get(self, ruleset_id: str, expect_ok: bool = True) -> Response:
        return self.request(
            "get",
            url=f"/objects/{self.domain}/{ruleset_id}",
            expect_ok=expect_ok,
        )


# === ContactGroup Endpoint Client ===


class ContactGroupTestClient(RestApiClient):
    domain: Literal["contact_group_config"] = "contact_group_config"

    def create(self, name: str, alias: str, expect_ok: bool = True) -> Response:
        body = {"name": name, "alias": alias}
        if version.is_managed_edition():
            body["customer"] = "provider"

        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )

    # TODO: Add other contact group endpoints


class HostTagGroupTestClient(RestApiClient):
    domain: Literal["host_tag_group"] = "host_tag_group"

    def create(
        self,
        ident: str,
        title: str,
        tags: list[dict[str, str | list[str]]],
        topic: str | None = None,
        help_text: str | None = None,
        expect_ok: bool = True,
    ) -> Response:
        body = {"ident": ident, "title": title, "tags": tags}
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

    def delete(self, ident: str, repair: bool = False, expect_ok: bool = True) -> Response:
        return self.request(
            "delete",
            url=f"/objects/{self.domain}/{ident}?repair={repair}",
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
        body: dict[str, Any] = {"ident": ident}
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


class PasswordTestClient(RestApiClient):
    domain: Literal["password"] = "password"

    def create(
        self,
        ident: str,
        title: str,
        owner: str,
        password: str,
        shared: Sequence[str],
        customer: str,
        expect_ok: bool = True,
    ) -> Response:
        body = {
            "ident": ident,
            "title": title,
            "owner": owner,
            "password": password,
            "shared": shared,
            "customer": customer,
        }
        return self.request(
            "post",
            url=f"/domain-types/{self.domain}/collections/all",
            body=body,
            expect_ok=expect_ok,
        )
