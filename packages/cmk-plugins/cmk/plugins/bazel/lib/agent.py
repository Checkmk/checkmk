#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_bazel_cache

This agent collects the metrics from https://bazel-cache-server/metrics.
Since this endpoint is public, no authentication is required.
"""

import argparse
import json
import re
import sys
import time
from collections.abc import Sequence
from typing import NamedTuple

import requests
import urllib3
from pydantic import BaseModel

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import report_agent_crashes, Storage, vcrtrace

from .semantic_version import SemanticVersion

__version__ = "2.6.0b1"

AGENT = "bazel_cache"

CAMEL_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")
DEFAULT_VERSION_CACHE_INTERVAL = 8 * 3600
PASSWORD_OPTION = "password"


class Endpoint(NamedTuple):
    name: str
    uri: str
    data_format: str = "text"


class BazelVersion(BaseModel):
    major: str | None
    minor: str | None
    patch: str | None


class BazelVersionInfo(BaseModel):
    timestamp: float
    current: str
    latest: BazelVersion


class VersionCache:
    VERSION_CACHE_KEY = "bazel_version_cache"

    def __init__(self, storage: Storage, ttl: float) -> None:
        self.storage = storage
        self.ttl = ttl

    def get_or_update(self, url: str, commit: str) -> BazelVersionInfo | None:
        return self._get_cached_version_info() or self._renew_cached_version_info(url, commit)

    def _get_cached_version_info(self) -> BazelVersionInfo | None:
        if not (raw := self.storage.read(self.VERSION_CACHE_KEY, None)):
            return None
        info = BazelVersionInfo.model_validate_json(raw)
        return info if (time.time() - info.timestamp) < self.ttl else None

    def _renew_cached_version_info(
        self, tags_url: str, commit_hash: str
    ) -> BazelVersionInfo | None:
        try:
            resp = requests.get(tags_url, timeout=30)
        except requests.exceptions.RequestException:
            return None
        timestamp = time.time()
        resp.raise_for_status()
        items = resp.json()
        versions = {
            item["commit"]["sha"]: SemanticVersion.from_string(item["name"]) for item in items
        }
        current_version = versions.get(commit_hash)

        if current_version is None:
            return None

        newer_versions = {v for v in versions.values() if v > current_version}
        majors = {v for v in newer_versions if v.major > current_version.major}
        minors = {v for v in newer_versions if v.minor > current_version.minor} - majors
        patches = {v for v in newer_versions if v.patch > current_version.patch} - majors - minors
        info = BazelVersionInfo(
            timestamp=timestamp,
            current=str(current_version),
            latest=BazelVersion(
                major=str(max(majors, default="")) or None,
                minor=str(max(minors, default="")) or None,
                patch=str(max(patches, default="")) or None,
            ),
        )
        # should the combination of url and commit actually be the key?
        self.storage.write(self.VERSION_CACHE_KEY, info.model_dump_json())
        return info


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(
            # This is the result of a refactoring.
            # I did not check if it makes sense for this special agent.
            filter_headers=[("authorization", "****")],
        ),
    )

    parser.add_argument("-u", "--user", help="Username for Bazel Cache login")
    parser_add_secret_option(
        parser, short="-p", long=f"--{PASSWORD_OPTION}", help="Bazel Cache password", required=False
    )
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help="Disable verification of the servers ssl certificate",
    )
    parser.add_argument("--host", required=True, help="Host name or IP address of Bazel Cache")
    parser.add_argument("--port", default=8080, type=int, help="Port for connection to Bazel Cache")
    parser.add_argument(
        "--protocol",
        default="https",
        choices=["http", "https"],
        help="Connection protocol to Bazel Cache",
    )
    parser.add_argument(
        "--version-cache",
        default=DEFAULT_VERSION_CACHE_INTERVAL,
        type=int,
        help=f"Cache interval in seconds for Bazel version collection (default: {DEFAULT_VERSION_CACHE_INTERVAL} [8h])",
    )
    parser.add_argument(
        "--bazel-cache-tags-url",
        default="https://api.github.com/repos/buchgr/bazel-remote/tags",
        help="GitHub compatible URL to get the tags of the Bazel Remote Cache project discover version information",
    )

    return parser.parse_args(argv)


def agent_bazel_cache_main(args: argparse.Namespace) -> int:
    endpoints = [
        Endpoint(
            name="status",
            uri="status",
            data_format="json",
        ),
        Endpoint(
            name="metrics",
            uri="metrics",
        ),
    ]

    return handle_requests(args, endpoints)


def handle_requests(args: argparse.Namespace, endpoints: list[Endpoint]) -> int:
    base_url = f"{args.protocol}://{args.host}:{args.port}"
    try:
        password = resolve_secret_option(args, PASSWORD_OPTION)
    except TypeError:
        password = None
    auth = (args.user, password.reveal()) if args.user and password else None

    if args.no_cert_check:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    for endpoint in endpoints:
        url = f"{base_url}{'/' if not endpoint.uri.startswith('/') else ''}{endpoint.uri}"

        # Get data from endpoint
        try:
            res = requests.get(
                url,
                auth=auth,
                timeout=10,
                verify=not args.no_cert_check,
            )
        except requests.exceptions.RequestException as e:
            sys.stderr.write("Error: %s\n" % e)
            if args.debug:
                raise
            return 1

        # Status code should be 200.
        if not res.status_code == requests.codes.OK:
            sys.stderr.write(
                f"Wrong status code: {res.status_code}. Expected: {requests.codes.OK} \n"
            )
            return 2

        # Check if something is returned at all
        if not res.content:
            sys.stderr.write(f"No data received from '{endpoint.name}' endpoint\n")
            return 3

        _process_data(res=res, endpoint=endpoint, args=args)

    return 0


def _camel_to_snake(name: str) -> str:
    return CAMEL_PATTERN.sub("_", name).lower()


def _process_data(res: requests.Response, endpoint: Endpoint, args: argparse.Namespace) -> None:
    if endpoint.data_format != "json":
        _process_txt_data(res=res, section_name=endpoint.name)
        return

    data = {_camel_to_snake(key): value for key, value in res.json().items()}
    sys.stdout.write(f"<<<bazel_cache_{endpoint.name}:sep(0)>>>\n")
    sys.stdout.write(f"{json.dumps(data)}\n")

    if endpoint.name != "status" or "git_commit" not in data:
        return

    version_cache = VersionCache(Storage(AGENT, args.host), args.version_cache)
    if not (
        version_info := version_cache.get_or_update(args.bazel_cache_tags_url, data["git_commit"])
    ):
        return

    sys.stdout.write("<<<bazel_cache_version:sep(0)>>>\n")
    sys.stdout.write(f"{version_info.model_dump_json()}\n")


def _process_txt_data(res: requests.Response, section_name: str) -> None:
    pattern = r'(\w+)="([^"]*)"'
    data = {}
    data_go = {}
    data_grpc = {}
    data_http = {}
    for line in res.text.splitlines():
        # # TYPE http_request_duration_seconds histogram
        # http_request_duration_seconds_bucket{code="401",handler="OPTIONS",method="OPTIONS",service="",le="0.5"} 2
        if not line.startswith("#"):
            splitted_line = line.split(" ")
            matches = re.findall(pattern, splitted_line[0])
            flatten_subkeys = "_".join("_".join(t) for t in matches if t[1] != "")
            key = f"{splitted_line[0].split('{')[0].lower()}{'_' + flatten_subkeys if flatten_subkeys else ''}".replace(
                ".", "_"
            )  # Holy Moly
            # http_request_duration_seconds_bucket_code_401_handler_OPTIONS_method_OPTIONS_le_0_5: 2

            if key.startswith("go_"):
                data_go[key] = splitted_line[-1]
            elif key.startswith("grpc_"):
                data_grpc[key] = splitted_line[-1]
            elif key.startswith("http_"):
                data_http[key] = splitted_line[-1]
            else:
                data[key] = splitted_line[-1]

    sys.stdout.write(
        f"<<<bazel_cache_{section_name}:sep(0)>>>\n"
        f"{json.dumps(data)}\n"
        f"<<<bazel_cache_{section_name}_go:sep(0)>>>\n"
        f"{json.dumps(data_go)}\n"
        f"<<<bazel_cache_{section_name}_grpc:sep(0)>>>\n"
        f"{json.dumps(data_grpc)}\n"
        f"<<<bazel_cache_{section_name}_http:sep(0)>>>\n"
        f"{json.dumps(data_http)}\n"
    )


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    args = parse_arguments(sys.argv[1:])
    return agent_bazel_cache_main(args)


if __name__ == "__main__":
    sys.exit(main())
