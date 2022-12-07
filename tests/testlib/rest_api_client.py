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
from collections.abc import Mapping
from typing import Any, NoReturn, Union

from pydantic import BaseModel, StrictStr

from cmk.utils.type_defs import HTTPMethod


class AuxTagJSON(BaseModel):
    aux_tag_id: StrictStr
    title: StrictStr
    topic: StrictStr


JSON = Union[int, str, bool, list[Any], dict[str, Any], None]
JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


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
                    "body": self.response.body,
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
    * call and return `self._request()` with the following args:
      * `url` should be the url of the endpoint with all path parameters filled in
      * `body` should be a dict with all the keys you inlined in to the function signature
      * `query_params` should be a dict with all the query parameters you inlined into the function signature
      * `expect_ok` should be passed on from the function signature
    * if the endpoint needs an etag, get it and pass it as a header to `self._request()` (see `edit_host`)

    A good example to start from would be the `create_host` method of this class.

    Please feel free to shuffle or convert function arguments if you believe it will increase the usability of the client.
    """

    def __init__(self, request_handler: RequestHandler, url_prefix: str):
        self._request_handler = request_handler
        self._url_prefix = url_prefix

    def _request(
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
    ) -> Response:
        default_headers = JSON_HEADERS.copy()
        default_headers.update(headers or {})

        if not url_is_complete:
            url = self._url_prefix + url

        if pydantic_basemodel_body is not None:
            request_body = pydantic_basemodel_body.json()
        else:
            if body is not None:
                request_body = json.dumps(body)
            else:
                request_body = ""

        resp = self._request_handler.request(
            method=method,
            url=url,
            query_params=query_params,
            body=request_body,
            headers=default_headers,
        )

        if expect_ok and resp.status_code >= 400:
            raise RestApiException(url, method, body, default_headers, resp)
        if follow_redirects and 300 <= resp.status_code < 400:
            return self._request(
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
        return self._request(**kwargs, url_is_complete=True, expect_ok=expect_ok)

    def get_folder(self, folder_name: str, expect_ok: bool = True) -> Response:
        return self._request(
            "get",
            url=f"/objects/folder_config/{folder_name}",
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
        return self._request(
            "put",
            url=f"/objects/folder_config/{folder_name}",
            headers=headers,
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
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
        return self._request(
            "post",
            url="/domain-types/host_config/collections/all",
            query_params=query_params,
            body={"host_name": host_name, "folder": folder, "attributes": attributes or {}},
            expect_ok=expect_ok,
        )

    def bulk_create_hosts(self, *args: JSON, expect_ok: bool = True) -> Response:
        return self._request(
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
        return self._request(
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
        return self._request("get", url="/objects/host_config/" + host_name, expect_ok=expect_ok)

    def edit_host(
        self,
        host_name: str,
        folder: str | None = None,
        attributes: Mapping[str, Any] | None = None,
        expect_ok: bool = True,
    ) -> Response:
        etag = self.get_host(host_name).headers["ETag"]
        headers = {"IF-Match": etag}
        body = {"host_name": host_name, "folder": folder, "attributes": attributes}
        return self._request(
            "put",
            url="/objects/host_config/" + host_name,
            body={k: v for k, v in body.items() if v is not None},
            expect_ok=expect_ok,
            headers=headers,
        )

    def bulk_edit_hosts(self, *args: JSON, expect_ok: bool = True) -> Response:
        return self._request(
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
        return self._request(
            "put",
            url=f"/objects/host_config/{host_name}/properties/{property_name}",
            body=property_value,
            headers=headers,
            expect_ok=expect_ok,
        )

    def delete_host(self, host_name: str) -> Response:
        return self._request("delete", url=f"/objects/host_config/{host_name}")

    def activate_changes(
        self,
        sites: list[str] | None = None,
        redirect: bool = False,
        force_foreign_changes: bool = False,
        expect_ok: bool = True,
    ) -> Response:
        if sites is None:
            sites = []
        return self._request(
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
        response = self._request(
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
                wait_response = self._request(
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

    def get_aux_tag(self, tag_id: str, expect_ok: bool = True) -> Response:
        return self._request(
            "get",
            url=f"/objects/aux_tag/{tag_id}",
            expect_ok=expect_ok,
        )

    def get_aux_tags(self, expect_ok: bool = True) -> Response:
        return self._request(
            "get",
            url="/domain-types/aux_tag/collections/all",
            expect_ok=expect_ok,
        )

    def create_aux_tag(self, tag_data: AuxTagJSON, expect_ok: bool = True) -> Response:
        return self._request(
            "post",
            url="/domain-types/aux_tag/collections/all",
            pydantic_basemodel_body=tag_data,
            expect_ok=expect_ok,
        )

    def edit_aux_tag(self, tag_data: AuxTagJSON, expect_ok: bool = True) -> Response:
        return self._request(
            "put",
            url=f"/objects/aux_tag/{tag_data.aux_tag_id}",
            body={"title": tag_data.title, "topic": tag_data.topic},
            expect_ok=expect_ok,
        )

    def delete_aux_tag(self, tag_id: str) -> Response:
        return self._request(
            "post",
            url=f"/objects/aux_tag/{tag_id}/actions/delete/invoke",
        )
