#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Special agent: agent_bazel_cache.

This agent collects the metrics from https://bazel-cache-server/metrics.
Since this endpoint is public, no authentication is required.
"""

import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple

import requests
import urllib3

from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.v0_unstable.misc import DataCache
from cmk.utils.paths import tmp_dir
from cmk.utils.semantic_version import SemanticVersion

CAMEL_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")
DEFAULT_VERSION_CACHE_INTERVAL = 8 * 3600


class Endpoint(NamedTuple):
    name: str
    uri: str
    data_format: str = "text"


class VersionCache(DataCache):
    def __init__(self, *, tags_url: str, interval: int, directory: Path | None = None) -> None:
        super().__init__(
            cache_file_dir=directory or (tmp_dir / "agents"),
            cache_file_name="bazel_cache_version",
        )
        self._url = tags_url
        self._interval = interval

    @property
    def cache_interval(self) -> int:
        return self._interval

    def get_validity_from_args(self, *args: Any) -> bool:
        return True

    def get_live_data(self, commit_hash: str) -> Any:
        resp = requests.get(self._url, timeout=30)
        resp.raise_for_status()
        items = resp.json()
        versions = {
            item["commit"]["sha"]: SemanticVersion.from_string(item["name"]) for item in items
        }
        current_version = versions.get(commit_hash)

        if current_version is not None:
            newer_versions = {v for k, v in versions.items() if v > current_version}
            majors = {v for v in newer_versions if v.major > current_version.major}
            minors = {v for v in newer_versions if v.minor > current_version.minor} - majors
            patches = (
                {v for v in newer_versions if v.patch > current_version.patch} - majors - minors
            )
            return {
                "current": str(current_version),
                "latest": {
                    "major": str(max(majors, default="")) or None,
                    "minor": str(max(minors, default="")) or None,
                    "patch": str(max(patches, default="")) or None,
                },
            }
        return None


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)

    parser.add_argument("-u", "--user", help="Username for Bazel Cache login")
    parser.add_argument("-p", "--password", help="Password for Bazel Cache login")
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


def agent_bazel_cache_main(args: Args) -> int:
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

    try:
        return handle_requests(args, endpoints)
    except Exception as e:
        if args.debug:
            raise e

    return 0


def handle_requests(args: Args, endpoints: list[Endpoint]) -> int:
    base_url = f"{args.protocol}://{args.host}:{args.port}"
    auth = (args.user, args.password) if args.user and args.password else None

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


def _process_data(res: requests.Response, endpoint: Endpoint, args: Args) -> None:
    if endpoint.data_format == "json":
        data = {_camel_to_snake(key): value for key, value in res.json().items()}
        if endpoint.name == "status" and "git_commit" in data:
            try:
                version_cache = VersionCache(
                    tags_url=args.bazel_cache_tags_url, interval=args.version_cache
                )
                version_data = version_cache.get_data(data["git_commit"])

                if version_data is not None:
                    with SectionWriter("bazel_cache_version") as writer:
                        writer.append_json(version_data)
            except requests.exceptions.RequestException:
                pass

        with SectionWriter(f"bazel_cache_{endpoint.name}") as writer:
            writer.append_json(data)
    else:
        _process_txt_data(res=res, section_name=endpoint.name)


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

    with SectionWriter(f"bazel_cache_{section_name}") as writer:
        writer.append_json(data)
    with SectionWriter(f"bazel_cache_{section_name}_go") as writer:
        writer.append_json(data_go)
    with SectionWriter(f"bazel_cache_{section_name}_grpc") as writer:
        writer.append_json(data_grpc)
    with SectionWriter(f"bazel_cache_{section_name}_http") as writer:
        writer.append_json(data_http)


def main() -> int:
    return special_agent_main(parse_arguments, agent_bazel_cache_main)


if __name__ == "__main__":
    sys.exit(main())
