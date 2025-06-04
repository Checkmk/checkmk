# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterable, Mapping, Sequence
from json import JSONDecodeError
from typing import Any

import requests

from cmk.special_agents.v0_unstable.agent_common import CannotRecover

LOGGER = logging.getLogger("agent_proxmox_ve.lib")

RequestStructure = Sequence[Mapping[str, Any]] | Mapping[str, Any]
TaskInfo = Mapping[str, Any]
LogData = Iterable[Mapping[str, Any]]  # [{"d": int, "t": str}, {}, ..]


class ProxmoxVeSession:
    """Session"""

    class HTTPAuth(requests.auth.AuthBase):
        """Auth"""

        def __init__(
            self,
            base_url: str,
            credentials: Mapping[str, str],
            timeout: int,
            verify_ssl: bool,
        ) -> None:
            super().__init__()
            ticket_url = base_url + "api2/json/access/ticket"
            response = (
                requests.post(url=ticket_url, verify=verify_ssl, data=credentials, timeout=timeout)
                .json()
                .get("data")
            )

            if response is None:
                raise CannotRecover(
                    "Couldn't authenticate {!r} @ {!r}".format(
                        credentials.get("username", "no-username"), ticket_url
                    )
                )

            self.pve_auth_cookie = response["ticket"]
            self.csrf_prevention_token = response["CSRFPreventionToken"]

        def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
            r.headers["CSRFPreventionToken"] = self.csrf_prevention_token
            return r

    def __init__(
        self,
        endpoint: tuple[str, int],
        credentials: Mapping[str, str],
        timeout: int,
        verify_ssl: bool,
    ) -> None:
        def create_session() -> requests.Session:
            session = requests.Session()
            session.auth = self.HTTPAuth(self._base_url, credentials, timeout, verify_ssl)
            session.cookies = requests.cookies.cookiejar_from_dict(
                {"PVEAuthCookie": session.auth.pve_auth_cookie}
            )
            session.headers["Connection"] = "keep-alive"
            session.headers["accept"] = ", ".join(
                (
                    "application/json",
                    "application/x-javascript",
                    "text/javascript",
                    "text/x-javascript",
                    "text/x-json",
                )
            )
            return session

        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._base_url = "https://%s:%d/" % endpoint
        self._session = create_session()

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """close connection to Proxmox VE endpoint"""
        self._session.close()

    def get_api_element(self, path: str) -> object:
        """do an API GET request"""
        try:
            return self._get_raw("api2/json/" + path)
        except requests.exceptions.ReadTimeout:
            raise CannotRecover(f"Read timeout after {self._timeout}s when trying to GET {path}")
        except requests.exceptions.ConnectionError as exc:
            raise CannotRecover(f"Could not GET element {path} ({exc})") from exc
        except JSONDecodeError as e:
            raise CannotRecover("Couldn't parse API element %r" % path) from e

    def _get_raw(self, sub_url: str) -> object:
        return (
            self._get_logs_or_tasks_paginated(sub_url)
            if (sub_url.endswith("/log") or sub_url.endswith("/tasks"))
            else self._validate_response(
                self._session.get(
                    url=self._base_url + sub_url,
                    verify=self._verify_ssl,
                    timeout=self._timeout,
                ),
                sub_url,
            )
        )

    def _get_logs_or_tasks_paginated(self, sub_url: str) -> list[object]:
        url = self._base_url + sub_url
        data: list[object] = []
        start = 0
        page_size = 5000

        while True:
            response_data = self._validate_response(
                self._session.get(
                    url=url,
                    verify=self._verify_ssl,
                    timeout=self._timeout,
                    params={"start": start, "limit": page_size},
                ),
                sub_url,
            )
            assert isinstance(response_data, Sequence)
            data += response_data

            if len(response_data) < page_size:
                break

            start += page_size

        return data

    @staticmethod
    def _validate_response(response: requests.Response, sub_url: str) -> object:
        if not response.ok:
            return []
        response_json = response.json()
        if "errors" in response_json:
            raise CannotRecover(
                "Could not fetch {!r} ({!r})".format(sub_url, response_json["errors"])
            )
        return response_json.get("data")


class ProxmoxVeAPI:
    """Wrapper for ProxmoxVeSession which provides high level API calls"""

    def __init__(
        self, host: str, port: int, credentials: Any, timeout: int, verify_ssl: bool
    ) -> None:
        try:
            LOGGER.info("Establish connection to Proxmox VE host %r", host)
            self._session = ProxmoxVeSession(
                endpoint=(host, port),
                credentials=credentials,
                timeout=timeout,
                verify_ssl=verify_ssl,
            )
        except requests.exceptions.ConnectTimeout:
            raise CannotRecover(f"Timeout after {timeout}s when trying to connect to {host}:{port}")
        except requests.exceptions.ConnectionError as exc:
            raise CannotRecover(f"Could not connect to {host}:{port} ({exc})") from exc

    def __enter__(self) -> Any:
        self._session.__enter__()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._session.__exit__(*exc_info)
        self._session.close()

    def get(self, path: str | Iterable[str]) -> Any:
        """Handle request items in form of 'path/to/item' or ['path', 'to', 'item']"""
        return self._session.get_api_element(
            path if isinstance(path, str) else "/".join(map(str, path))
        )

    def get_tree(self, requested_structure: RequestStructure) -> Any:
        def rec_get_tree(
            element_name: str | None,
            requested_structure: RequestStructure,
            path: Iterable[str],
        ) -> Any:
            """Recursively fetch data from API to match <requested_structure>"""

            def is_list_of_subtree_names(data: RequestStructure) -> bool:
                """Return True if given data is a list of dicts containing names of subtrees,
                e.g [{'name': 'log'}, {'name': 'options'}, ...]"""
                return bool(data) and all(
                    isinstance(elem, Mapping) and tuple(elem) in {("name",), ("subdir",), ("cmd",)}
                    for elem in data
                )

            def extract_request_subtree(request_tree: RequestStructure) -> RequestStructure:
                """If list if given return first (and only) element return the provided data tree"""
                return (
                    request_tree
                    if isinstance(request_tree, Mapping)
                    else next(iter(request_tree))
                    if len(request_tree) > 0
                    else {}
                )

            def extract_variable(st: RequestStructure) -> Mapping[str, Any] | None:
                """Check if there is exactly one root element with a variable name,
                e.g. '{node}' and return its stripped name"""
                if not isinstance(st, Mapping):
                    return None
                if len(st) != 1 or not next(iter(st)).startswith("{"):
                    # we have either exactly one variable or no variables at all
                    assert len(st) != 1 or all(not e.startswith("{") for e in st)
                    return None
                key, value = next(iter(st.items()))
                assert len(st) == 1 and key.startswith("{")
                return {"name": key.strip("{}"), "subtree": value}

            next_path = list(path) + ([] if element_name is None else [element_name])
            subtree = extract_request_subtree(requested_structure)
            variable = extract_variable(subtree)
            response = self._session.get_api_element("/".join(map(str, next_path)))

            if isinstance(response, Sequence):
                # Handle subtree stubs like [{'name': 'log'}, {'name': 'options'}, ...]
                if is_list_of_subtree_names(response):
                    assert variable is None
                    assert not isinstance(requested_structure, Sequence) and isinstance(
                        subtree, Mapping
                    )
                    assert subtree
                    subdir_names = (
                        (
                            elem[
                                next(
                                    identifier
                                    for identifier in ("name", "subdir", "cmd")
                                    if identifier in elem
                                )
                            ]
                        )
                        for elem in response
                    )
                    return {
                        key: rec_get_tree(key, subtree[key], next_path)
                        for key in subdir_names
                        if key in subtree
                    }

                # Handle case when response is a list of arbitrary datasets
                #  e.g [{'uptime': 12345}, 'id': 'server-1', ...}, ...]"""
                if all(isinstance(elem, Mapping) for elem in response):
                    if variable is None:
                        assert isinstance(subtree, Mapping)
                        return (
                            {key: rec_get_tree(key, subtree[key], next_path) for key in subtree}
                            if isinstance(requested_structure, Mapping)
                            else response
                        )  #

                    assert isinstance(requested_structure, Sequence)
                    return [
                        {
                            **elem,
                            **(
                                rec_get_tree(
                                    elem[variable["name"]],
                                    variable["subtree"],
                                    next_path,
                                )
                                or {}
                            ),
                        }
                        for elem in response
                    ]

            return response

        return rec_get_tree(None, requested_structure, [])
