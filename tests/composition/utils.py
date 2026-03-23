#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import glob
import json
import logging
import subprocess
import time
from pathlib import Path

from tests.testlib.agent import get_package_type, wait_for_baking_job
from tests.testlib.site import Site

logger = logging.getLogger("composition-tests")
logger.setLevel(logging.INFO)


class Timeout(RuntimeError):
    pass


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
    # On Checkmk Community we can't bake agents since agent baking is a commercial feature so we
    # use the vanilla agent
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


def enable_rabbitmq_tracing(*sites: Site) -> None:
    """
    - cmk-monitor-broker --enable_tracing does two things:
        (a) runs rabbitmq-plugins enable rabbitmq_tracing which persists to the enabled_plugins file, and
        (b) binds the trace log via the management API (which does not persist across RabbitMQ restarts)
    - RabbitMQ only starts once PIGGYBACK_HUB is turned on, so tracing can only be enabled after that
    - trace log binding won't survive a site restart (e.g., during _turn_off_piggyback_hub).
      The plugin itself will, because rabbitmq-plugins enable modifies enabled_plugins.
    - therefore:
        1. This should be called, if needed, after every RabbitMQ restart
        2. there should be NO NEED to disable tracing; it's basically disabled automatically
           when RAbbitMQ is restarted; disabling it only adds incerased risk of flakes.
    """
    for site in sites:
        site.run(["cmk-monitor-broker", "--enable_tracing"])


def await_broker_ready(*sites: Site) -> None:
    # restart of rabbitmq needs re-enabling of tracing
    enable_rabbitmq_tracing(*sites)
    for site in sites:
        _await_port_ready(site)
        _await_shovels_ready(site)


def _await_port_ready(site: Site) -> None:
    port = int(site.omd("config", "show", "RABBITMQ_PORT", check=True).stdout)
    for _ in range(60):
        if site.execute(["rabbitmq-diagnostics", "check_port_listener", str(port)]).wait() == 0:
            return
        time.sleep(1)
    raise Timeout(f"Rabbitmq did not start properly (port {port} not listening)")


def _await_shovels_ready(site: Site) -> None:
    for _ in range(60):
        try:
            raw = site.run(["rabbitmqctl", "shovel_status", "--formatter", "json"]).stdout
        except subprocess.CalledProcessError as e:
            logger.exception(
                "Failed to get shovel status on %s (rc=%s, stdout=%r, stderr=%r); waiting...",
                site.id,
                e.returncode,
                e.stdout,
                e.stderr,
            )
            time.sleep(1)
            continue

        data = json.loads(raw)
        if all(shovel["state"] == "running" for shovel in data):
            return
        logger.info("Shovels on %s are not running. Waiting...", site.id)
        time.sleep(1)
    raise Timeout("Rabbitmq shovels not started properly.")
