#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import dataclasses
import json
import pathlib
import sys
from collections.abc import Collection, Sequence
from typing import Protocol, Self

import requests

from cmk.utils import password_store
from cmk.utils.semantic_version import SemanticVersion

from cmk.plugins.gerrit.lib.shared_typing import SectionName, Sections
from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser


def main() -> int:
    """Entrypoint for Gerrit special agent."""
    return special_agent_main(parse_arguments, run_agent)


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse commandline arguments passed to special agent."""
    parser = create_default_argument_parser(description=__doc__)

    parser.add_argument("-u", "--user", default="", help="Username for Gerrit login")
    group_password = parser.add_mutually_exclusive_group(required=True)
    group_password.add_argument(
        "--password-ref",
        help="Password store reference to the secret password for your Gerrit account.",
    )
    group_password.add_argument("-s", "--password", help="Password for Gerrit login")
    parser.add_argument(
        "-P",
        "--proto",
        choices=("https", "http"),
        default="https",
        help="Protocol (default: 'https')",
    )
    parser.add_argument("-p", "--port", default=443, type=int, help="Port (default: 443)")
    parser.add_argument("hostname", metavar="HOSTNAME", help="Hostname of Gerrit instance.")

    return parser.parse_args(argv)


def run_agent(args: Args) -> int:
    """Run Gerrit special agent."""
    api_url = f"{args.proto}://{args.hostname}:{args.port}/a"
    auth = (args.user, get_password_from_args(args))

    collector = SyncSectionCollector(api_url=api_url, auth=auth)
    sections = collect_sections(collector)
    write_sections(sections)

    return 0


def get_password_from_args(args: Args) -> str:
    """Extract password from store if explicit password not passed as argument."""
    if args.password:
        return args.password

    pw_id, pw_file = args.password_ref.split(":", maxsplit=1)

    return password_store.lookup(pathlib.Path(pw_file), pw_id)


class SectionCollector(Protocol):
    """An interface for collecting agent sections."""

    def collect(self) -> Sections:
        """Collect Gerrit related data grouped by section."""


def collect_sections(collector: SectionCollector) -> Sections:
    """Send off requests and collect the results."""
    return collector.collect()


def write_sections(sections: Sections) -> None:
    """Write out sections to the special agent output."""
    for name, data in sections.items():
        with SectionWriter(f"gerrit_{name}") as writer:
            writer.append_json(data)


@dataclasses.dataclass
class LatestVersions:
    """Latest release major, minor, and patch version, if available."""

    major: str | None
    minor: str | None
    patch: str | None

    @classmethod
    def build(cls, current: SemanticVersion, versions: Collection[SemanticVersion]) -> Self:
        """Search for potential updates based on the current and provided versions."""
        return cls(
            major=str(max((v for v in versions if v.major > current.major), default="")) or None,
            minor=str(max((v for v in versions if v.minor > current.minor), default="")) or None,
            patch=str(max((v for v in versions if v.patch > current.patch), default="")) or None,
        )


class SyncSectionCollector:
    """Client for collecting sections synchronously."""

    def __init__(self, api_url: str, auth: tuple[str, str]) -> None:
        self.api_url = api_url
        self.auth = auth

    def collect(self) -> Sections:
        current_version = self._get_current_section()
        latest_versions = self._get_latest_versions(current_version)

        return {
            SectionName("version"): {
                "current": str(current_version),
                "latest": dataclasses.asdict(latest_versions),
            },
        }

    def _get_current_section(self) -> SemanticVersion:
        uri = "/config/server/version?verbose"

        resp = requests.get(self.api_url + uri, auth=self.auth, timeout=30)
        resp.raise_for_status()

        clean_content = resp.content.lstrip(b")]}'")  # prefixed with )]}' for security
        data = json.loads(clean_content)

        return SemanticVersion.from_string(data["gerrit_version"])

    @staticmethod
    def _get_latest_versions(current: SemanticVersion) -> LatestVersions:
        gerrit_releases_url = "https://www.googleapis.com/storage/v1/b/gerrit-releases/o"
        query = "?projection=noAcl&fields=items(name)&matchGlob=gerrit-[0-9]*.[0-9]*.[0-9]*.war"

        resp = requests.get(gerrit_releases_url + query, timeout=30)
        resp.raise_for_status()

        versions = {SemanticVersion.from_string(item["name"]) for item in resp.json()["items"]}

        return LatestVersions.build(current, versions)


if __name__ == "__main__":
    sys.exit(main())
