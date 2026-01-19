#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Literal, NamedTuple

from git.objects.commit import Commit
from git.repo import Repo

from cmk.werks import load_werk, parse_werk

from .constants import NON_WERK_FILES_IN_WERK_FOLDER
from .models import AllWerks, WebsiteWerkV2, WebsiteWerkV3

logger = logging.getLogger(__name__)


class Config:
    """
    We read werks from different git repositories, and each repo has its own
    quirks. This config tries to hold all repo specific configuration.
    """

    def __init__(self, flavor: Literal["cma", "cmk", "checkmk_kube_agent", "cloudmk"]) -> None:
        self.flavor = flavor

    # only branches matching this regex will be considered for searching for
    # werk files.
    branch_regex: str

    def cleanup_branch_name(self, branch_name: str) -> str:
        # in previous releases of cmk there were branches called 1.2.7i3
        # but we want to store the werks in 1.2.7, we use this function to
        # adapt this.
        return branch_name

    def adapt_werk_string(self, werk_string: str, werk_id: int) -> str:  # noqa: ARG002
        # there is one faulty werk in cmk repo, but in many branches
        # its easier to fix here...
        return werk_string


def branch_name_to_sort(branch_name: str) -> tuple[str | int, ...]:
    """
    >>> sorted(["master", "2.1.0", "main", "2.1.0i1"], key=branch_name_to_sort)
    ['2.1.0i1', '2.1.0', 'main', 'master']

    """
    if branch_name in {"master", "main"}:
        return (99, 99, 99, 99, branch_name)
    result = re.match(r"(\d+)\.(\d+)\.(\d+)(i(\d))?$", branch_name)
    if not result:
        logger.info("can not sort branch %s", branch_name)
        return (0, 0, 0, 0, branch_name)
    major, minor, patch, _, innovation = result.groups()
    if innovation is None:
        innovation = 99
    return (int(major), int(minor), int(patch), int(innovation), branch_name)


class WerkFile(NamedTuple):
    file_name: str
    file_content: bytes


def _get_branches(
    r: Repo, c: Config, branch_replacement: Mapping[str, str]
) -> Iterable[tuple[str, Commit]]:
    if branch_replacement:
        for branch, ref in branch_replacement.items():
            yield branch, r.commit(ref)
        return

    for ref in r.remote().refs:  # type: ignore[assignment]
        if not ref.name.startswith("origin/"):  # type: ignore[attr-defined]
            logger.info("ignoring ref %s (only considering one from remote origin)", ref)
            continue

        branch_name = ref.name.removeprefix("origin/")  # type: ignore[attr-defined]
        if not re.match(c.branch_regex, branch_name):
            logger.info("ignoring branch %s (does not match regex)", branch_name)
            continue
        yield branch_name, ref  # type: ignore[misc]


def main(config: Config, repo_path: Path, branches: Mapping[str, str]) -> None:
    logging.basicConfig()
    c = config

    werk_files_by_id_and_branch: dict[int, dict[str, WerkFile]] = defaultdict(dict)
    r = Repo(repo_path)
    for branch_name, ref in _get_branches(r, c, branches):
        tree = r.tree(ref)
        try:
            werks = tree[".werks"]
        except KeyError:
            logger.warning("no .werks folder in branch %s", branch_name)
            continue

        for werk_file in werks.blobs:
            werk_id_str = werk_file.name.removesuffix(".md")
            try:
                werk_id = int(werk_id_str)
            except ValueError as e:
                if werk_file.name in NON_WERK_FILES_IN_WERK_FOLDER:
                    continue
                raise RuntimeError(
                    f"Found unexpected file {werk_file.name!r} in branch {branch_name!r}"
                ) from e
            werk_files_by_id_and_branch[werk_id][branch_name] = WerkFile(
                file_name=werk_file.name, file_content=werk_file.data_stream.read()
            )

    werk_string = None
    all_werks_by_id: dict[str, WebsiteWerkV2 | WebsiteWerkV3] = {}
    for werk_id, werk_by_branch in werk_files_by_id_and_branch.items():
        versions: dict[str, str] = {}
        # werks are defined multiple times, the werk that is defined in the "latest" branch wins.
        # that's why we sort here by branch name...
        for branch, werk_file in sorted(
            werk_by_branch.items(), key=lambda i: branch_name_to_sort(i[0])
        ):
            werk_string = werk_file.file_content.decode("utf-8")
            werk_string = c.adapt_werk_string(werk_string, werk_id)

            try:
                parsed = parse_werk(werk_string, werk_file.file_name)
            except Exception as e:
                raise RuntimeError(
                    f"could not parse werk {werk_file.file_name} from "
                    f"branch {branch} of flavor {config.flavor}"
                ) from e
            versions[c.cleanup_branch_name(branch)] = parsed.metadata["version"]

        try:
            # and here we simply access variables of the latest werk iteration above.
            assert werk_string is not None
            werk = load_werk(
                file_content=werk_string, file_name=werk_file.file_name
            )  # this could be optimized, as we now parse the werk twice.
        except Exception as e:
            raise RuntimeError(f"could not load werk {werk_id} from flavor {config.flavor}") from e

        werk_dict = {k: v for k, v in werk.to_json_dict().items() if v is not None}
        werk_dict.pop("version")
        website_werk: WebsiteWerkV2 | WebsiteWerkV3
        if werk_dict["__version__"] == "2":
            website_werk = WebsiteWerkV2(
                versions=versions,
                product=config.flavor,
                **werk_dict,  # type: ignore[arg-type]
            )
        elif werk_dict["__version__"] == "3":
            website_werk = WebsiteWerkV3(
                versions=versions,
                product=config.flavor,
                **werk_dict,  # type: ignore[arg-type]
            )
        else:
            raise RuntimeError()
        all_werks_by_id[str(werk_id)] = website_werk

    sys.stdout.write(AllWerks.dump_json(all_werks_by_id, by_alias=True).decode("utf-8") + "\n")
