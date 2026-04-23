#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Site configuration and config hooks

Hooks are scripts in lib/omd/hooks that are being called with one
of the following arguments:

default - return the default value of the hook. Mandatory
set     - implements a new setting for the hook
choices - available choices for enumeration hooks
depends - exits with 1, if this hook misses its dependent hook settings
"""

import dataclasses
import os
import re
import subprocess
import sys
import traceback
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING

from omdlib.config_choices import (
    ApacheNetworkPortHasError,
    ApacheTCPAddrHasError,
    ConfigChoiceHasError,
    IpAddressListHasError,
    IpListenAddressHasError,
    NetworkPortHasError,
)
from omdlib.site_paths import SitePaths
from omdlib.sites import all_sites
from omdlib.type_defs import Config

from cmk.ccc.exceptions import MKTerminate
from cmk.ccc.version import edition

if TYPE_CHECKING:
    from omdlib.contexts import SiteContext

ConfigHookChoiceItem = tuple[str, str]
ConfigHookChoices = Pattern[str] | list[ConfigHookChoiceItem] | ConfigChoiceHasError
ConfigHookResult = tuple[int, str]


class _Error: ...


@dataclasses.dataclass(frozen=True)
class _SiteConfigs:
    configs: Mapping[str, Config]
    sites_with_unreadable_configs: Sequence[str]


@dataclasses.dataclass(frozen=True)
class ConfigHook:
    choices: ConfigHookChoices
    name: str
    description: str
    alias: str
    menu: str
    unstructured: dict[str, bool]


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
def load_config_hooks(site: "SiteContext", verbose: bool) -> ConfigHooks:
    config_hooks: ConfigHooks = {}

    hook_files = []
    if site.hook_dir:
        hook_files = os.listdir(site.hook_dir)

    for hook_name in hook_files:
        try:
            if hook_name[0] != ".":
                hook = _config_load_hook(site, hook_name, verbose)
                config_hooks[hook_name] = hook
        except MKTerminate:
            raise
        except Exception:
            pass
    config_hooks = load_hook_dependencies(site, config_hooks, verbose)
    return config_hooks


def _config_load_hook(
    site: "SiteContext",
    hook_name: str,
    verbose: bool,
) -> ConfigHook:
    unstructured = {"deprecated": False}

    if not site.hook_dir:
        # IMHO this should be unreachable...
        raise MKTerminate("Site has no version and therefore no hooks")

    alias = None
    description = ""
    menu = "Other"
    description_active = False
    with Path(site.hook_dir, hook_name).open() as hook_file:
        for line in hook_file:
            if line.startswith("# Alias:"):
                alias = line[8:].strip()
            elif line.startswith("# Menu:"):
                menu = line[7:].strip()
            elif line.startswith("# Deprecated: yes"):
                unstructured["deprecated"] = True
            elif line.startswith("# Description:"):
                description_active = True
            elif line.startswith("#  ") and description_active:
                description += line[3:].strip() + "\n"
            else:
                description_active = False

    hook_info = _call_hook(site, hook_name, ["choices"], verbose)[1]
    assert alias is not None, "Implementation error, please contact support"
    return ConfigHook(
        choices=_parse_hook_choices(hook_info),
        name=hook_name,
        alias=alias,
        menu=menu,
        description=description,
        unstructured=unstructured,
    )


def _parse_hook_choices(hook_info: str) -> ConfigHookChoices:
    # The choices can either be a list of possible keys. Then
    # the hook outputs one live for each choice where the key and a
    # description are separated by a colon. Or it outputs one line
    # where that line is an extended regular expression matching the
    # possible values.

    match [choice.strip() for choice in hook_info.split("\n")]:
        case [""]:
            raise MKTerminate("Invalid output of hook: empty output")
        case ["@{IP_LISTEN_ADDRESS}"]:
            return IpListenAddressHasError()
        case ["@{NETWORK_PORT}"]:
            return NetworkPortHasError()
        case ["@{APACHE_NETWORK_PORT}"]:
            return ApacheNetworkPortHasError()
        case ["@{IP_ADDRESS_LIST}"]:
            return IpAddressListHasError()
        case ["@{APACHE_TCP_ADDR}"]:
            return ApacheTCPAddrHasError()
        case [regextext]:
            return re.compile(regextext + "$")
        case choices_list:
            try:
                choices: list[ConfigHookChoiceItem] = []
                for line in choices_list:
                    val, descr = line.split(":", 1)
                    choices.append((val.strip(), descr.strip()))
            except ValueError as excep:
                raise MKTerminate(f"Invalid output of hook: {choices_list}: {excep}") from excep
            return choices


def load_hook_dependencies(
    site: "SiteContext", config_hooks: ConfigHooks, verbose: bool
) -> ConfigHooks:
    for hook_name in _sort_hooks(list(config_hooks.keys())):
        hook = config_hooks[hook_name]
        exitcode, _content = _call_hook(site, hook_name, ["depends"], verbose)
        if exitcode:
            hook.unstructured["active"] = False
        else:
            hook.unstructured["active"] = True
    return config_hooks


def load_config(site: "SiteContext", verbose: bool) -> Config:
    """Load all variables from omd/sites.conf. These variables always begin with
    CONFIG_. The reason is that this file can be sources with the shell.

    Puts these variables into the config dict without the CONFIG_. Also
    puts the variables into the process environment."""
    site_home = SitePaths.from_site_name(site.name).home
    config = read_site_config(site_home)
    if site.hook_dir and os.path.exists(site.hook_dir):
        for hook_name in _sort_hooks(os.listdir(site.hook_dir)):
            if hook_name[0] != "." and hook_name not in config:
                config[hook_name] = _call_hook(
                    site, hook_name, ["default", edition(Path(site_home)).long], verbose
                )[1]
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


def _call_hook(
    site: "SiteContext", hook_name: str, args: list[str], verbose: bool
) -> ConfigHookResult:
    if not site.hook_dir:
        # IMHO this should be unreachable...
        raise MKTerminate("Site has no version and therefore no hooks")

    cmd = [site.hook_dir + hook_name] + args
    hook_env = os.environ.copy()
    hook_env.update(
        {
            "OMD_ROOT": SitePaths.from_site_name(site.name).home,
            "OMD_SITE": site.name,
        }
    )

    if verbose:
        sys.stdout.write("Calling hook: " + subprocess.list2cmdline(cmd) + "\n")

    completed_process = subprocess.run(
        cmd,
        env=hook_env,
        close_fds=True,
        shell=False,
        encoding="utf-8",
        check=False,
        capture_output=True,
    )
    # `sys.stderr` is a magically replaced during `omd update`. During all other situations just
    # removing `stderr=subprocess.PIPE` and the line below should be completely equivalent.
    sys.stderr.write(completed_process.stderr)
    content = completed_process.stdout.strip()

    if completed_process.returncode and args[0] != "depends":
        sys.stderr.write(f"Error running {subprocess.list2cmdline(cmd)}: {content}\n")

    return completed_process.returncode, content


def config_set_all(
    site: "SiteContext", config: Config, verbose: bool, ignored_hooks: Sequence[str]
) -> None:
    for hook_name in _sort_hooks(list(config.keys())):
        # Hooks may vanish after and up- or downdate
        if not _hook_exists(site, hook_name):
            continue

        if hook_name in ignored_hooks:
            continue

        _config_set(site, config, hook_name, verbose)


def _report_error(key: str, sites_with_unreadable_configs: Sequence[str]) -> None:
    if sites_with_unreadable_configs:
        sites_str = ",".join(sites_with_unreadable_configs)
        sys.stderr.write(
            f"ERROR: Failed to read config of site {sites_str}. "
            f"{key} port will possibly be allocated twice\n"
        )


def _config_set(
    site: "SiteContext",
    config: Config,
    hook_name: str,
    verbose: bool,
    omd_path: Path = Path("/omd/"),
) -> None:
    value = config[hook_name]
    match hook_name:
        case "LIVESTATUS_TCP_PORT":
            site_configs = _build_site_configs(site.name, omd_path)
            _report_error("LIVESTATUS_TCP_PORT", site_configs.sites_with_unreadable_configs)
            output = _set_livestatus_tcp_port(site.name, value, site_configs.configs, omd_path)
            if isinstance(output, _Error):
                return
        case _:
            exitcode, output = _call_hook(site, hook_name, ["set", value], verbose)
            if exitcode:
                return
    if output:
        config[hook_name] = output

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


def _set_livestatus_tcp_port(
    site_name: str, value: str, site_configs: Mapping[str, Config], omd_path: Path = Path("/omd/")
) -> str | _Error:
    site_home = SitePaths.from_site_name(site_name, omd_path).home
    try:
        new_value = str(_next_free_port("LIVESTATUS_TCP_PORT", site_name, int(value), site_configs))
        pattern = re.compile(r"^(\s*port\s*=\s*)([0-9]+)")
        xinetd_conf = os.path.join(site_home, "etc/mk-livestatus/xinetd.conf")
        if value != new_value:
            sys.stderr.write(
                f"Livestatus port {value} is in use. I've choosen {new_value} instead."
            )

        with open(xinetd_conf) as file:
            lines = file.readlines()

        with open(xinetd_conf, "w") as file:
            for line in lines:
                new_line = pattern.sub(rf"\g<1>{new_value}", line)
                file.write(new_line)
    except Exception:
        traceback.print_exc()
        return _Error()
    return new_value


def config_set_value(
    site: "SiteContext",
    site_home: str,
    config: Config,
    hook_name: str,
    value: str,
    verbose: bool,
    save: bool = True,
) -> None:
    config[hook_name] = value
    _config_set(site, config, hook_name, verbose)

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
