#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import glob
import logging
import time
from pathlib import Path

from tests.testlib.agent import get_package_type, wait_for_baking_job
from tests.testlib.site import Site

logger = logging.getLogger("composition-tests")
logger.setLevel(logging.INFO)


def get_package_extension() -> str:
    package_type = get_package_type()
    if package_type == "linux_deb":
        return "deb"
    if package_type == "linux_rpm":
        return "rpm"
    raise NotImplementedError(
        f"'get_package_extension' for '{package_type}' is not supported yet in, please implement it"
    )


def bake_agent(site: Site, hostname: str) -> tuple[str, Path]:
    logger.info('Create host "%s" and bake agent...', hostname)
    start_time = time.time()
    if site.openapi.hosts.get(hostname):
        site.openapi.hosts.delete(hostname)
    site.openapi.hosts.create(
        hostname,
        attributes={"ipaddress": site.http_address},
        bake_agent=True,
    )
    site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)

    # A baking job just got triggered automatically after adding the host. wait for it to finish.
    wait_for_baking_job(site, start_time)

    server_rel_hostlink_dir = Path("var", "check_mk", "agents", get_package_type(), "references")
    agent_path = site.resolve_path(server_rel_hostlink_dir / hostname)
    agent_hash = agent_path.name

    return agent_hash, agent_path


def get_cre_agent_path(site: Site) -> Path:
    # On CRE we can't bake agents since agent baking is a CEE feature so we use the vanilla agent
    package_extension = get_package_extension()
    agent_folder = site.resolve_path(Path("share", "check_mk", "agents"))
    # The locations of the 2 agent packages in the raw edition are:
    # *) $SITE_HOME/share/check_mk/agents/check-mk-agent_2022.11.08-1_all.deb
    # *) $SITE_HOME/share/check_mk/agents/check-mk-agent-2022.11.08-1.noarch.rpm
    agent_search_pattern = agent_folder / f"check-mk-agent*.{package_extension}"
    agent_results = list(glob.glob(agent_search_pattern.as_posix()))
    if not agent_results:
        raise ValueError(
            f"Can't find '{package_extension}' agent to install in folder '{agent_folder}'"
        )
    return Path(agent_results[0])
