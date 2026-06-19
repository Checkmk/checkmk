#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
import os
import subprocess
import sys
import traceback
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from omdlib.admin_mail import ADMIN_MAIL
from omdlib.agent_receiver import AGENT_RECEIVER, AGENT_RECEIVER_PORT
from omdlib.automation_helper import AUTOMATION_HELPER
from omdlib.autostart import AUTOSTART
from omdlib.config_api import Config, Hook, PortHook
from omdlib.core import CORE
from omdlib.jaeger import (
    TRACE_JAEGER_ADMIN_PORT,
    TRACE_JAEGER_UI_PORT,
    TRACE_RECEIVE,
    TRACE_RECEIVE_ADDRESS,
    TRACE_RECEIVE_PORT,
    TRACE_SEND,
    TRACE_SEND_TARGET,
    TRACE_SERVICE_NAMESPACE,
)
from omdlib.liveproxyd import LIVEPROXYD
from omdlib.livestatus import (
    LIVESTATUS_TCP,
    LIVESTATUS_TCP_INSTANCES,
    LIVESTATUS_TCP_ONLY_FROM,
    LIVESTATUS_TCP_PER_SOURCE,
    LIVESTATUS_TCP_PORT,
    LIVESTATUS_TCP_TLS,
)
from omdlib.mkeventd import MKEVENTD, MKEVENTD_SNMPTRAP, MKEVENTD_SYSLOG, MKEVENTD_SYSLOG_TCP
from omdlib.multisite import MULTISITE_AUTHORISATION, MULTISITE_COOKIE_AUTH
from omdlib.opentelemetry import (
    OPENTELEMETRY_COLLECTOR,
    OPENTELEMETRY_COLLECTOR_SELF_MONITORING_PORT,
)
from omdlib.piggyback_hub import PIGGYBACK_HUB
from omdlib.pnp4nagios import PNP4NAGIOS
from omdlib.rabbitmq import (
    RABBITMQ_DIST_PORT,
    RABBITMQ_MANAGEMENT_PORT,
    RABBITMQ_ONLY_FROM,
    RABBITMQ_PORT,
)
from omdlib.site_paths import SitePaths
from omdlib.sites import all_sites
from omdlib.system_apache import (
    APACHE_MODE,
    APACHE_TCP_ADDR,
    APACHE_TCP_PORT,
)
from omdlib.tmpfs import TMPFS

from cmk.ccc.exceptions import MKTerminate
from cmk.ccc.version import edition

if TYPE_CHECKING:
    from omdlib.contexts import SiteContext

ConfigHookResult = tuple[int, str]


@dataclasses.dataclass(frozen=True)
class _SiteConfigs:
    configs: Mapping[str, Config]
    sites_with_unreadable_configs: Sequence[str]


@dataclasses.dataclass(frozen=True)
class ConfigHook:
    name: str
    description: str
    alias: str
    menu: str


ConfigHooks = dict[str, ConfigHook]


# Put all site configuration (explicit and defaults) into environment
# variables beginning with CONFIG_
def create_config_environment(config: Config) -> None:
    for varname, value in config.items():
        os.environ["CONFIG_" + varname] = value


# TODO: RENAME
def save_site_conf(site_home: str, config: Config) -> None:
    confdir = Path(site_home, "etc/omd")
    confdir.mkdir(exist_ok=True)
    with (confdir / "site.conf").open(mode="w") as f:
        for hook_name, value in sorted(config.items(), key=lambda x: x[0]):
            f.write(f"CONFIG_{hook_name}='{value}'\n")
    (confdir / "site.conf").chmod(0o644)


# Get information about all hooks. Just needed for
# the "omd config" command.
def load_config_hooks(hook_dir: str | None) -> ConfigHooks:
    config_hooks: ConfigHooks = {}

    hook_files = []
    if hook_dir:
        hook_files = os.listdir(hook_dir)

    for hook_name in hook_files:
        try:
            if hook_name[0] != ".":
                hook = _config_load_hook(hook_dir, hook_name)
                config_hooks[hook_name] = hook
        except MKTerminate:
            raise
        except Exception:
            pass
    return config_hooks


def _config_load_hook(hook_dir: str | None, hook_name: str) -> ConfigHook:
    if not hook_dir:
        # IMHO this should be unreachable...
        raise MKTerminate("Site has no version and therefore no hooks")

    alias = None
    description = ""
    menu = "Other"
    description_active = False
    with Path(hook_dir, hook_name).open() as hook_file:
        for line in hook_file:
            if line.startswith("# Alias:"):
                alias = line[8:].strip()
            elif line.startswith("# Menu:"):
                menu = line[7:].strip()
            elif line.startswith("# Description:"):
                description_active = True
            elif line.startswith("#  ") and description_active:
                description += line[3:].strip() + "\n"
            else:
                description_active = False

    assert alias is not None, "Implementation error, please contact support"
    return ConfigHook(name=hook_name, alias=alias, menu=menu, description=description)


_HOOKS: Sequence[Hook | PortHook] = [
    ADMIN_MAIL,
    AGENT_RECEIVER,
    AGENT_RECEIVER_PORT,
    APACHE_MODE,
    APACHE_TCP_ADDR,
    APACHE_TCP_PORT,
    AUTOMATION_HELPER,
    AUTOSTART,
    CORE,
    LIVEPROXYD,
    LIVESTATUS_TCP,
    LIVESTATUS_TCP_INSTANCES,
    LIVESTATUS_TCP_ONLY_FROM,
    LIVESTATUS_TCP_PER_SOURCE,
    LIVESTATUS_TCP_PORT,
    LIVESTATUS_TCP_TLS,
    MKEVENTD,
    MKEVENTD_SNMPTRAP,
    MKEVENTD_SYSLOG,
    MKEVENTD_SYSLOG_TCP,
    MULTISITE_AUTHORISATION,
    MULTISITE_COOKIE_AUTH,
    OPENTELEMETRY_COLLECTOR,
    OPENTELEMETRY_COLLECTOR_SELF_MONITORING_PORT,
    PIGGYBACK_HUB,
    PNP4NAGIOS,
    RABBITMQ_DIST_PORT,
    RABBITMQ_MANAGEMENT_PORT,
    RABBITMQ_ONLY_FROM,
    RABBITMQ_PORT,
    TMPFS,
    TRACE_JAEGER_ADMIN_PORT,
    TRACE_JAEGER_UI_PORT,
    TRACE_RECEIVE,
    TRACE_RECEIVE_ADDRESS,
    TRACE_RECEIVE_PORT,
    TRACE_SEND,
    TRACE_SEND_TARGET,
    TRACE_SERVICE_NAMESPACE,
]


def load_hook_dependencies(config: Config, config_hooks: ConfigHooks) -> dict[str, bool]:
    return {hook_name: _get_hook(hook_name).depends(config) for hook_name in config_hooks}


def _default_port(site_name: str, port_hook: PortHook, site_configs: _SiteConfigs) -> str:
    _report_error(port_hook.name, site_configs.sites_with_unreadable_configs)
    return str(
        _next_free_port(port_hook.name, site_name, port_hook.default_port, site_configs.configs)
    )


def load_config(site: "SiteContext", omd_path: Path = Path("/omd/")) -> Config:
    """Load all variables from omd/sites.conf. These variables always begin with
    CONFIG_. The reason is that this file can be sources with the shell.

    Puts these variables into the config dict without the CONFIG_. Also
    puts the variables into the process environment."""
    site_home = SitePaths.from_site_name(site.name, omd_path).home
    config = read_site_config(site_home)
    site_configs = _build_site_configs(site.name, omd_path)
    if site.hook_dir and os.path.exists(site.hook_dir):
        for hook_name in _sort_hooks(os.listdir(site.hook_dir)):
            if hook_name[0] != "." and hook_name not in config:
                hook = _get_hook(hook_name)
                if isinstance(hook, PortHook):
                    config[hook_name] = _default_port(site.name, hook, site_configs)
                else:
                    config[hook_name] = hook.default(edition(Path(site_home)))
    return config


def read_site_config(site_home: str) -> Config:
    """Read and parse the file site.conf of a site into a dictionary and returns it"""
    config: Config = {}
    if not (confpath := Path(site_home, "etc/omd/site.conf")).exists():
        return {}

    with confpath.open() as conf_file:
        for line in conf_file:
            line = line.strip()
            if line == "" or line[0] == "#":
                continue
            var, value = line.split("=", 1)
            if not var.startswith("CONFIG_"):
                sys.stderr.write("Ignoring invalid variable %s.\n" % var)
            else:
                config[var[7:].strip()] = value.strip().strip("'")

    return config


# Always sort CORE hook to the end because it runs "cmk -U" which
# relies on files created by other hooks.
def _sort_hooks(hook_names: list[str]) -> Iterable[str]:
    return sorted(hook_names, key=lambda n: (n == "CORE", n))


def _hook_exists(site: "SiteContext", hook_name: str) -> bool:
    if not site.hook_dir:
        return False
    hook_file = site.hook_dir + hook_name
    return os.path.exists(hook_file)


def config_set_all(site: "SiteContext", config: Config, ignored_hooks: Sequence[str]) -> None:
    for hook_name in _sort_hooks(list(config.keys())):
        # Hooks may vanish after and up- or downdate
        if not _hook_exists(site, hook_name):
            continue

        if hook_name in ignored_hooks:
            continue

        _config_set(site.name, config, hook_name)


def _report_error(key: str, sites_with_unreadable_configs: Sequence[str]) -> None:
    if sites_with_unreadable_configs:
        sites_str = ",".join(sites_with_unreadable_configs)
        sys.stderr.write(
            f"ERROR: Failed to read config of site {sites_str}. "
            f"{key} port will possibly be allocated twice\n"
        )


def _get_hook(hook_name: str) -> Hook | PortHook:
    for hook in _HOOKS:
        if hook.name == hook_name:
            return hook
    assert False, "Implementation error, please contact support"


def _config_set(
    site_name: str,
    config: Config,
    hook_name: str,
    omd_path: Path = Path("/omd/"),
) -> None:
    site_home = Path(SitePaths.from_site_name(site_name).home)

    hook = _get_hook(hook_name)
    if isinstance(hook, PortHook):
        site_configs = _build_site_configs(site_name, omd_path)
        _report_error(hook_name, site_configs.sites_with_unreadable_configs)
        value = config[hook_name]
        new_value = str(_next_free_port(hook_name, site_name, int(value), site_configs.configs))
        if value != new_value:
            sys.stderr.write(
                f"{hook.display_name} {value} is in use. I've chosen {new_value} instead.\n"
            )
        config[hook_name] = new_value
    try:
        hook.activation(site_name, site_home, config)
    except Exception:
        traceback.print_exc()
        return

    os.environ["CONFIG_" + hook_name] = config[hook_name]


def _build_site_configs(this_site: str, omd_path: Path = Path("/omd")) -> _SiteConfigs:
    site_configs: dict[str, Config] = {}
    sites_with_unreadable_configs = []
    for sitename in all_sites(omd_path):
        site_home = SitePaths.from_site_name(sitename, omd_path).home
        if sitename == this_site:
            site_configs[sitename] = read_site_config(site_home)
        else:
            try:
                config = read_site_config(site_home)
            except PermissionError:
                sites_with_unreadable_configs.append(sitename)
                continue
            if not config:
                sites_with_unreadable_configs.append(sitename)
                continue
            site_configs[sitename] = config
    return _SiteConfigs(site_configs, sites_with_unreadable_configs)


def _port_is_used(key: str, this_site: str, port: str, site_configs: Mapping[str, Config]) -> bool:
    for sitename, config in site_configs.items():
        if sitename == this_site:
            if any(k != key and port == v for k, v in config.items()):
                return True
        elif any(port == v for v in config.values()):
            return True
    return False


def _next_free_port(
    key: str, this_site: str, start_port: int, site_configs: Mapping[str, Config]
) -> int:
    while _port_is_used(key, this_site, str(start_port), site_configs):
        start_port += 1
    return start_port


def config_set_value(
    site: "SiteContext",
    site_home: str,
    config: Config,
    hook_name: str,
    value: str,
    save: bool = True,
) -> None:
    config[hook_name] = value
    _config_set(site.name, config, hook_name)

    if hook_name in ["CORE", "MKEVENTD", "PNP4NAGIOS"]:
        update_cmk_core_config(site_home, config)

    if save:
        save_site_conf(SitePaths.from_site_name(site.name).home, config)


def update_cmk_core_config(site_home: str, config: Config) -> None:
    if config["CORE"] == "none":
        return  # No core config is needed in this case

    sys.stdout.write("Updating core configuration...\n")
    try:
        # TODO: try to find an easier way to create the default config!
        subprocess.check_call(
            ["cmk", "-U"],
            env={
                **os.environ,
                "PASSWORD_STORE_SECRET_FILE": f"{site_home}/etc/password_store.secret",
            },
            shell=False,
        )
    except subprocess.SubprocessError:
        sys.exit("Could not update core configuration. Aborting.")
