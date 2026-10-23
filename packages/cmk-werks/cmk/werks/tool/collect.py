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
from typing import NamedTuple

from git.objects.commit import Commit
from git.repo import Repo

from cmk.werks.tool import parse_werk

from .constants import NON_WERK_FILES_IN_WERK_FOLDER
from .flavor import Flavor
from .models import AllWerks, WebsiteWerkV2, WebsiteWerkV3

logger = logging.getLogger(__name__)


def branch_name_to_sort(branch_name: str) -> tuple[str | int, ...]:
    """
    >>> sorted(["master", "2.1.0", "main", "2.1.0i1"], key=branch_name_to_sort)
    ['2.1.0i1', '2.1.0', 'main', 'master']

    """
    if branch_name in {"master", "main"}:
        return (99, 99, 99, 99, branch_name)
    result = re.match(r"(\d+)\.(\d+)\.(\d+)(i(\d))?$", branch_name)
    if not result:
        logger.info("can not sort branch %(branch)s", {"branch": branch_name})
        return (0, 0, 0, 0, branch_name)
    major, minor, patch, _, innovation = result.groups()
    if innovation is None:
        innovation = 99
    return (int(major), int(minor), int(patch), int(innovation), branch_name)


class WerkFile(NamedTuple):
    file_name: str
    file_content: bytes


def _get_branches(
    r: Repo, c: Flavor, branch_replacement: Mapping[str, str]
) -> Iterable[tuple[str, Commit]]:
    if branch_replacement:
        for branch, rev in branch_replacement.items():
            yield branch, r.commit(rev)
        return

    for ref in r.remote().refs:
        if not ref.name.startswith("origin/"):
            logger.info(
                "ignoring ref %(ref)s (only considering one from remote origin)", {"ref": ref}
            )
            continue

        branch_name = ref.name.removeprefix("origin/")
        if not re.match(c.branch_regex, branch_name):
            logger.info(
                "ignoring branch %(branch)s (does not match regex)", {"branch": branch_name}
            )
            continue
        yield branch_name, ref.commit


def main(flavor: Flavor, repo_path: Path, branches: Mapping[str, str]) -> None:
    logging.basicConfig()
    c = flavor

    defines_make_version_by_branch: dict[str, str] = {}
    werk_files_by_id_and_branch: dict[int, dict[str, WerkFile]] = defaultdict(dict)
    r = Repo(repo_path)
    for branch_name, ref in _get_branches(r, c, branches):
        tree = r.tree(ref)

        version = flavor.read_current_version(tree)
        if version is None:
            logger.warning(
                "could not determine the next release version in branch %(branch)s",
                {"branch": branch_name},
            )
            continue

        defines_make_version_by_branch[branch_name] = version

        try:
            werks = tree[".werks"]
        except KeyError:
            logger.warning("no .werks folder in branch %(branch)s", {"branch": branch_name})
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
                parsed = parse_werk(
                    werk_string, werk_file.file_name, v1_defaults=flavor.v1_defaults
                )
            except Exception as e:
                raise RuntimeError(
                    f"could not parse werk {werk_file.file_name} from "
                    f"branch {branch} of flavor {flavor.name}"
                ) from e
            if (werk_version := parsed.metadata.get("version")) is None:
                # if there is no version in the werk itself,
                # we assume the werk will be released with the next release
                werk_version = defines_make_version_by_branch[branch]
            versions[c.cleanup_branch_name(branch)] = werk_version

        try:
            # and here we simply access variables of the latest werk iteration above.
            assert werk_string is not None
            werk = flavor.load_werk(
                file_content=werk_string, file_name=werk_file.file_name
            )  # this could be optimized, as we now parse the werk twice.
        except Exception as e:
            raise RuntimeError(f"could not load werk {werk_id} from flavor {flavor.name}") from e

        werk_dict = {k: v for k, v in werk.to_json_dict().items() if v is not None}
        werk_dict.pop("version", None)
        all_werks_by_id[str(werk_id)] = WebsiteWerkV3.model_validate(
            werk_dict | {"versions": versions, "product": flavor.name}
        )

    if not all_werks_by_id:
        raise RuntimeError("Expected to collect at least one Werk, but it's completely empty.")

    sys.stdout.write(AllWerks.dump_json(all_werks_by_id, by_alias=True).decode("utf-8") + "\n")
