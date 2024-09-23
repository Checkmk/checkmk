#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Literal

from cmk.werks.collect import Config
from cmk.werks.collect import main as collect_main

logger = logging.getLogger(__name__)


class CmaConfig(Config):
    branch_regex = r"^(master$|\d+\.\d+$)"


class CmkConfig(Config):
    branch_regex = r"^master$|^\d+\.\d+\.\d+"

    def cleanup_branch_name(self, branch_name: str) -> str:
        """
        >>> CmkConfig("cmk").cleanup_branch_name("1.5.0i3")
        '1.5.0'

        >>> CmkConfig("cmk").cleanup_branch_name("1.5.0")
        '1.5.0'

        >>> [CmkConfig("cmk").cleanup_branch_name(v) for v in [ "1.2.5", "1.2.6", "1.2.7", "1.2.8"]]
        ['1.2.0', '1.2.0', '1.2.0', '1.2.0']
        """
        if branch_name.startswith("1.2."):
            return "1.2.0"
        return re.sub(r"(i\d+)$", "", branch_name)

    def adapt_werk_string(self, werk_string: str, werk_id: int) -> str:
        if werk_id == 1281:
            # werk 1281 of cmk is missing a newline, but it is available in
            # multiple branches so we fix it here
            return werk_string.replace("Class: feature", "Class: feature\n")
        if werk_id == 3229:
            # don't want to commit to branch 1.2.8
            return werk_string.replace("name inventorized\\", "name inventorized")
        if werk_id in {1071, 198, 4045, 10589, 7032, 10579}:
            return _replace_compatible(werk_string, "compat")
        if werk_id in {4914, 4737, 10303, 11202, 11277, 7048, 11159, 11475}:
            return _replace_compatible(werk_string, "incomp")
        if werk_id == 13164:
            return werk_string.replace("<PC_NAME>", "&lt;PC_NAME>")
        if werk_id == 13488:
            return werk_string.replace("<tt>postgres_conn_time</tt>:", "postgres_conn_time:")
        if werk_id == 5141:
            return werk_string.replace(
                "parameter <tt>request_format</tt>", "parameter request_format"
            )
        return werk_string


COMP_MATCHER = re.compile("^Compatible: (comp|multisite|incompat|imcompat|compa)$")


def _replace_compatible(werk_string: str, compatible: str) -> str:
    def generator() -> Iterator[str]:
        for line in werk_string.split("\n"):
            if COMP_MATCHER.match(line):
                line = f"Compatible: {compatible}"
            yield line
            yield "\n"

    return "".join(generator())


class KubeConfig(Config):
    branch_regex = r"^(main$|\d+\.\d+\.\d+)"


def config_from_flavor(flavor: Literal["cma", "cmk", "checkmk_kube_agent"]) -> "Config":
    if flavor == "cma":
        return CmaConfig(flavor)
    if flavor == "checkmk_kube_agent":
        return KubeConfig(flavor)
    if flavor == "cmk":
        return CmkConfig(flavor)
    raise NotImplementedError()


def main(
    flavor: Literal["cma", "cmk", "checkmk_kube_agent"],
    repo_path: Path,
    branches: Mapping[str, str],
) -> None:
    collect_main(config_from_flavor(flavor), repo_path, branches)
