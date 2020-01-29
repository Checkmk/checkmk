#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | "_ \ / _ \/ __| |/ /   | |\/| | " /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright tribe29 2020                                           |
# +------------------------------------------------------------------+
#
# This file is part of Checkmk
# The official homepage is at https://checkmk.de.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""
Checkmk ProxMox special agent
"""

# Read:
# - https://pve.proxmox.com/wiki/Proxmox_VE_API
# - https://pve.proxmox.com/pve-docs/api-viewer/
# - https://pve.proxmox.com/pve-docs/api-viewer/apidoc.js
# - https://pypi.org/project/proxmoxer/

# Todo:
# - Backup Status VMs & Container, Gesamtstatus + piggybacked
# - Replication Status VMs & Container, Gesamtstatus + piggybacked
# - Snapshots - piggybacked
# - PVE Version im Check_MK Output
# - Status der VMs & Container, z.b. Staus/lock reason/maxdisc/maxmem/name - piggybacked bzw.
#    siehe auch pvesh get /cluster/resources

# pylint: disable=too-few-public-methods

import sys
import json
import argparse
import logging
from typing import Any, List, Tuple, Dict, Union, Optional

import requests
from requests.packages import urllib3

import cmk.utils.password_store

# cannot be imported yet - pathlib2 is missing for python3
# from cmk.special_agents.utils import vcrtrace

ListOrDict = Union[List[Dict[str, Any]], Dict[str, Any]]


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    """parse command line arguments and return argument object"""
    parser = argparse.ArgumentParser(description=__doc__)
    # needs import vcrtrace which needs pathlib2
    # parser.add_argument("--vcrtrace", action=vcrtrace(filter_headers=[('authorization', '****')]))
    parser.add_argument('--timeout', '-t', type=int, default=20, help='API call timeout')
    parser.add_argument('--port', type=int, default=8006, help='IPv4 port to connect to')
    parser.add_argument('--username', '-u', type=str, help='username for connection')
    parser.add_argument('--password', '-p', type=str, help='password for connection')
    parser.add_argument('--verbose', '-v', action="count", default=0)
    # TODO: default should not be True
    parser.add_argument('--no-cert-check', action="store_true", default=True)
    parser.add_argument('--debug', action="store_true", help="Keep some exceptions unhandled")
    parser.add_argument("hostname", help="Name of the ProxMox instance to query.")

    return parser.parse_args(argv)


def write_agent_output(args: argparse.Namespace) -> None:
    """Fetches and writes selected information formatted as agent output to stdout"""
    def write_piggyback_sections(host: str, sections: List[Dict[str, Any]]) -> None:
        print("<<<<%s>>>>" % host)
        write_sections(sections)

    def write_sections(sections: List[Dict[str, Any]]) -> None:
        def write_section(*, name: str, data: Any, jsonify: bool = True) -> None:
            print(("<<<%s:sep(0)>>>" if jsonify else "<<<%s>>>") % name)
            print(json.dumps(data, sort_keys=True) if jsonify else data)

        for section in sections:
            write_section(**section)

    with ProxmoxAPI(
            host=args.hostname,
            port=args.port,
            credentials={k: getattr(args, k) for k in {"username", "password"} if getattr(args, k)},
            timeout=args.timeout,
            verify_ssl=not args.no_cert_check,
    ) as session:
        data = session.get_tree({
            "cluster": {
                "backup": [],
            },
            "nodes": [{
                "{node}": {
                    "subscription": {},
                    "lxc": [],
                    "qemu": [],
                },
            }],
            "version": {},
        })

        write_sections([{
            "name": "proxmox_version",
            "data": data["version"],
        }])
        for node in data["nodes"]:
            write_piggyback_sections(
                host=node['node'],
                sections=[
                    {
                        "name": "uptime",
                        "data": node["uptime"],
                        "jsonify": False,
                    },
                    {
                        "name": "proxmox_node_subscription",
                        "data": node["subscription"],
                        "jsonify": True,
                    },
                ],
            )


class ProxmoxSession:
    """Session"""
    class HTTPAuth(requests.auth.AuthBase):
        """Auth"""
        def __init__(self, base_url: str, credentials: Dict[str, str], timeout: int,
                     verify_ssl: bool) -> None:
            super().__init__()
            ticket_url = base_url + "api2/json/access/ticket"
            response = requests.post(url=ticket_url,
                                     verify=verify_ssl,
                                     data=credentials,
                                     timeout=timeout).json().get("data")
            if response is None:
                raise RuntimeError("Couldn't authenticate %r @ %r" %
                                   (credentials.get('username', "no-username"), ticket_url))

            self.pve_auth_cookie = response["ticket"]
            self.csrf_prevention_token = response["CSRFPreventionToken"]

        def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
            r.headers["CSRFPreventionToken"] = self.csrf_prevention_token
            return r

    def __init__(self, *, endpoint: Tuple[str, int], credentials: Dict[str, str], timeout: int,
                 verify_ssl: bool) -> None:
        def create_session() -> requests.Session:
            session = requests.Session()
            session.auth = self.HTTPAuth(self._base_url, credentials, timeout, verify_ssl)
            session.cookies = requests.cookies.cookiejar_from_dict(  # type: ignore
                {"PVEAuthCookie": session.auth.pve_auth_cookie})
            session.headers['Connection'] = 'keep-alive'
            session.headers["accept"] = ", ".join(
                ("application/json", "application/x-javascript", "text/javascript",
                 "text/x-javascript", "text/x-json"))
            return session

        super().__init__()
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._base_url = "https://%s:%d/" % endpoint
        self._session = create_session()

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *_args: Any, **_kwargs: Any) -> None:
        self.close()

    def close(self) -> None:
        """close connection to ProxMox endpoint"""
        if self._session:
            self._session.close()

    def get_raw(self, sub_url: str) -> requests.Response:
        return self._session.request(
            method="GET",
            url=self._base_url + sub_url,
            verify=self._verify_ssl,
            timeout=self._timeout,
        )

    def get_api_element(self, path: str) -> Any:
        """do an API GET request"""
        response_json = self.get_raw("api2/json/" + path).json()
        if 'errors' in response_json:
            raise RuntimeError("could not fetch %r (%r)" % (path, response_json['errors']))
        return response_json.get('data')


class ProxmoxAPI:
    """Wrapper for ProxmoxSession which provides high level API calls"""
    def __init__(self, *, host: str, port: int, credentials: Any, timeout: int,
                 verify_ssl: bool) -> None:
        self._session = ProxmoxSession(
            endpoint=(host, port),
            credentials=credentials,
            timeout=timeout,
            verify_ssl=verify_ssl,
        )

    def __enter__(self) -> Any:
        self._session.__enter__()
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        self._session.__exit__(*args, **kwargs)
        self._session.close()

    def get(self, path: Union[str, List[str], Tuple[str]]) -> Any:
        """Handle request items in form of 'path/to/item' or ['path', 'to', 'item'] """
        return self._session.get_api_element("/".join(
            str(p) for p in path) if isinstance(path, (list, tuple)) else path)

    def get_tree(self, requested_structure: ListOrDict) -> Any:
        def rec_get_tree(
                element_name: Optional[str],
                requested_structure: ListOrDict,
                path: List[str],
        ) -> Any:
            """Recursively fetch data from API to match <requested_structure>"""
            def is_list_of_subtree_names(data: ListOrDict) -> bool:
                """Return True if given data is a list of dicts containing names of subtrees,
                e.g [{'name': 'log'}, {'name': 'options'}, ...]"""
                return bool(data) and all(
                    isinstance(elem, dict) and tuple(elem) in {("name",), ("subdir",), ("cmd",)}  #
                    for elem in data)

            def extract_request_subtree(request_tree: ListOrDict) -> ListOrDict:
                """If list if given return first (and only) element return the provided data tree"""
                return (request_tree if not isinstance(request_tree, list) else  #
                        next(iter(request_tree)) if len(request_tree) > 0 else {})

            def extract_variable(st: ListOrDict) -> Optional[Dict[str, Any]]:
                """Check if there is exactly one root element with a variable name,
                e.g. '{node}' and return its stripped name"""
                if not isinstance(st, dict):
                    return None
                if len(st) != 1 or not next(iter(st)).startswith("{"):
                    # we have either exactly one variable or no variables at all
                    assert len(st) != 1 or all(not e.startswith("{") for e in st)
                    return None
                key, value = next(iter(st.items()))
                assert len(st) == 1 and key.startswith("{")
                return {"name": key.strip("{}"), "subtree": value}

            next_path = path + ([str(element_name)] if element_name is not None else [])
            subtree = extract_request_subtree(requested_structure)
            variable = extract_variable(subtree)
            response = self._session.get_api_element("/".join(next_path))

            log().info("%r <%s>: %30s", "/".join(next_path), type(response).__name__, str(response))

            if isinstance(response, list):
                # Handle subtree stubs like [{'name': 'log'}, {'name': 'options'}, ...]
                if is_list_of_subtree_names(response):
                    assert variable is None
                    assert not isinstance(requested_structure, list) and isinstance(subtree, dict)
                    assert subtree
                    subdir_names = ((elem[next(identifier
                                               for identifier in ('name', 'subdir', 'cmd')
                                               if identifier in elem)])
                                    for elem in response)
                    return {
                        key: rec_get_tree(key, subtree[key], next_path)
                        for key in subdir_names
                        if key in subtree
                    }

                # Handle case when response is a list of arbitrary datasets
                #  e.g [{'uptime': 12345}, 'id': 'server-1', ...}, ...]"""
                if all(isinstance(elem, dict) for elem in response):
                    assert isinstance(requested_structure, list)
                    return response if variable is None else [
                        {
                            **key,
                            **(rec_get_tree(key[variable["name"]], variable["subtree"], next_path) or {})
                        }  #
                        for key in response
                    ]

            return response

        return rec_get_tree(None, requested_structure, [])


def log() -> logging.Logger:
    return logging.getLogger("agent_proxmox")


def main(argv: Any = None) -> int:
    """read arguments, configure application and run command specified on command line"""
    if argv is None:
        cmk.utils.password_store.replace_passwords()
        argv = sys.argv[1:]
    args = parse_arguments(argv)

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # type: ignore
    logging.basicConfig(level={
        0: logging.WARN,
        1: logging.INFO,
        2: logging.DEBUG
    }.get(args.verbose, logging.WARN))

    # activate as soon as vcr is available (see imports)
    # logging.getLogger("vcr").setLevel(logging.WARN)

    try:
        write_agent_output(args)
    except Exception as exc:
        if args.debug:
            raise
        log().error("Cought exception: %r", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
