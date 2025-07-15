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
from collections.abc import Iterable
from ipaddress import ip_network, IPv4Address, IPv6Address
from pathlib import Path
from re import Pattern
from typing import override, TYPE_CHECKING

import pydantic

from omdlib.type_defs import Config, ConfigChoiceHasError

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import MKTerminate
from cmk.ccc.version import edition

from cmk.utils import paths

if TYPE_CHECKING:
    from omdlib.contexts import SiteContext
from omdlib.site_paths import SitePaths

ConfigHookChoiceItem = tuple[str, str]
ConfigHookChoices = Pattern | list[ConfigHookChoiceItem] | ConfigChoiceHasError
ConfigHookResult = tuple[int, str]


@dataclasses.dataclass(frozen=True)
class ConfigHook:
    choices: ConfigHookChoices
    name: str
    description: str
    alias: str
    menu: str
    unstructured: dict[str, bool]


ConfigHooks = dict[str, ConfigHook]


class IpAddressListHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        ip_addresses = value.split()
        if not ip_addresses:
            return result.Error("Specify at least one IP address.")
        for ip_address in ip_addresses:
            try:
                ip_network(ip_address)
            except ValueError:
                return result.Error(f"The IP address {ip_address} does match the expected format.")
        return result.OK(None)


class IpListenAddressHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        if not value:
            return result.Error("Empty address")

        if value.startswith("[") and value.endswith("]"):
            try:
                IPv6Address(value[1:-1])
                return result.OK(None)
            except ValueError:
                return result.Error("Invalid IPv6 address")

        try:
            IPv4Address(value)
        except ValueError:
            return result.Error("Invalid IPv4 address")

        return result.OK(None)


class NetworkPortHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        try:
            port = int(value)
        except ValueError:
            return result.Error("Invalid port number")

        if port < 1024 or port > 65535:
            return result.Error("Invalid port number")

        return result.OK(None)


class ApacheTCPAddrHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        class _Parser(pydantic.RootModel):
            root: pydantic.HttpUrl

        url = f"http://{value}:80"
        try:
            _Parser.model_validate(url)
            return result.OK(None)
        except pydantic.ValidationError as e:
            message = f"""OMD uses APACHE_TCP_ADDR and APACHE_TCP_PORT to construct an Apache
Listen directive. For example, setting APACHE_TCP_PORT to 80 results in: {url}.
This is invalid because of: """
            message += ", ".join([error["ctx"]["error"] for error in e.errors()])
            return result.Error(message)


# Put all site configuration (explicit and defaults) into environment
# variables beginning with CONFIG_
def create_config_environment(site: "SiteContext") -> None:
    for varname, value in site.conf.items():
        os.environ["CONFIG_" + varname] = value


# TODO: RENAME
def save_site_conf(site: "SiteContext") -> None:
    confdir = Path(SitePaths.from_site_name(site.name).home, "etc/omd")
    confdir.mkdir(exist_ok=True)
    with (confdir / "site.conf").open(mode="w") as f:
        for hook_name, value in sorted(site.conf.items(), key=lambda x: x[0]):
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
                # only load configuration hooks
                if hook.choices is not None:
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

    hook_info = call_hook(site, hook_name, ["choices"], verbose)[1]
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
    for hook_name in sort_hooks(list(config_hooks.keys())):
        hook = config_hooks[hook_name]
        exitcode, _content = call_hook(site, hook_name, ["depends"], verbose)
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
        for hook_name in sort_hooks(os.listdir(site.hook_dir)):
            if hook_name[0] != "." and hook_name not in config:
                config[hook_name] = call_hook(
                    site, hook_name, ["default", edition(paths.omd_root).short], verbose
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
def sort_hooks(hook_names: list[str]) -> Iterable[str]:
    return sorted(hook_names, key=lambda n: (n == "CORE", n))


def hook_exists(site: "SiteContext", hook_name: str) -> bool:
    if not site.hook_dir:
        return False
    hook_file = site.hook_dir + hook_name
    return os.path.exists(hook_file)


def call_hook(
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
        sys.stdout.write("Calling hook: " + subprocess.list2cmdline(cmd))

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
