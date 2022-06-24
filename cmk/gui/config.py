#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import errno
import os
import sys
from dataclasses import asdict, dataclass, field, fields, make_dataclass
from functools import partial
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Tuple, Union

from livestatus import SiteConfiguration, SiteConfigurations

import cmk.utils.paths
import cmk.utils.tags
import cmk.utils.version as cmk_version
from cmk.utils.site import omd_site, url_prefix

import cmk.gui.i18n
import cmk.gui.log as log
import cmk.gui.utils as utils
from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import MKConfigError
from cmk.gui.i18n import _

# Kept for compatibility with pre 1.6 GUI plugins
from cmk.gui.permissions import (  # noqa: F401 # pylint: disable=unused-import
    declare_permission,
    declare_permission_section,
)
from cmk.gui.plugins.config.base import CREConfig
from cmk.gui.type_defs import Key

if not cmk_version.is_raw_edition():
    from cmk.gui.cee.plugins.config.cee import CEEConfig  # pylint: disable=no-name-in-module
else:
    # Stub needed for non enterprise edition
    class CEEConfig:  # type: ignore[no-redef]
        pass


if cmk_version.is_managed_edition():
    from cmk.gui.cme.plugins.config.cme import CMEConfig  # pylint: disable=no-name-in-module
else:

    # Stub needed for non managed services edition
    class CMEConfig:  # type: ignore[no-redef]
        pass


#   .--Declarations--------------------------------------------------------.
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Declarations of global variables and constants                      |
#   '----------------------------------------------------------------------'

# hard coded in various permissions
builtin_role_ids: List[str] = ["user", "admin", "guest"]


@dataclass
class Config(CREConfig, CEEConfig, CMEConfig):
    """Holds the loaded configuration during GUI processing

    The loaded configuration is then accessible through `from cmk.gui.globals import config`.
    For builtin config variables type checking and code completion works.

    This class is extended by `load_config` to support custom config variables which may
    be introduced by 3rd party extensions. For these variables we don't have the features
    mentioned above. But that's fine for now.
    """

    tags: cmk.utils.tags.TagConfig = cmk.utils.tags.TagConfig()


active_config: Config = request_local_attr("config")


# .
#   .--Functions-----------------------------------------------------------.
#   |             _____                 _   _                              |
#   |            |  ___|   _ _ __   ___| |_(_) ___  _ __  ___              |
#   |            | |_ | | | | '_ \ / __| __| |/ _ \| '_ \/ __|             |
#   |            |  _|| |_| | | | | (__| |_| | (_) | | | \__ \             |
#   |            |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper functions for config parsing, login, etc.                    |
#   '----------------------------------------------------------------------'


def initialize() -> None:
    load_config()
    log.set_log_levels(active_config.log_levels)
    cmk.gui.i18n.set_user_localizations(active_config.user_localizations)


def _load_config_file_to(path: str, raw_config: Dict[str, Any]) -> None:
    """Load the given GUI configuration file"""
    try:
        with Path(path).open("rb") as f:
            exec(f.read(), {}, raw_config)
    except IOError as e:
        if e.errno != errno.ENOENT:  # No such file or directory
            raise
    except Exception as e:
        raise MKConfigError(_("Cannot read configuration file %s: %s:") % (path, e))


# Load multisite.mk and all files in multisite.d/. This will happen
# for *each* HTTP request.
# FIXME: Optimize this to cache the config etc. until either the config files or plugins
# have changed. We could make this being cached for multiple requests just like the
# plugins of other modules. This may save significant time in case of small requests like
# the graph ajax page or similar.
def load_config() -> None:
    # Set default values for all user-changable configuration settings
    raw_config = get_default_config()

    # Initialize sites with default site configuration. Need to do it here to
    # override possibly deleted sites
    raw_config["sites"] = default_single_site_configuration()

    # Load assorted experimental parameters if any
    experimental_config = cmk.utils.paths.make_experimental_config_file()
    if experimental_config.exists():
        _load_config_file_to(str(experimental_config), raw_config)

    # First load main file
    _load_config_file_to(cmk.utils.paths.default_config_dir + "/multisite.mk", raw_config)

    # Load also recursively all files below multisite.d
    conf_dir = cmk.utils.paths.default_config_dir + "/multisite.d"
    filelist = []
    if os.path.isdir(conf_dir):
        for root, _directories, files in os.walk(conf_dir):
            for filename in files:
                if filename.endswith(".mk"):
                    filelist.append(root + "/" + filename)

    filelist.sort()
    for p in filelist:
        _load_config_file_to(p, raw_config)

    raw_config["sites"] = prepare_raw_site_config(raw_config["sites"])
    raw_config["tags"] = cmk.utils.tags.get_effective_tag_config(raw_config["wato_tags"])

    # TODO: Temporary local hack to transform the values to the correct type. This needs
    # to be done in make_config_object() in the next step.
    if "agent_signature_keys" in raw_config:
        raw_config["agent_signature_keys"] = {
            key_id: Key.parse_obj(raw_key)
            for key_id, raw_key in raw_config["agent_signature_keys"].items()
        }

    # Make sure, builtin roles are present, even if not modified and saved with WATO.
    for br in builtin_role_ids:
        raw_config["roles"].setdefault(br, {})

    request_local_attr().config = make_config_object(raw_config)

    execute_post_config_load_hooks()


def make_config_object(raw_config: Dict[str, Any]) -> Config:
    """Create the runtime config object

    In case there are some custom extensions installed which introduce new config variables, we make
    us compatible by creating a dynamic class which makes the Config class accept the required
    values. Since it is dynamic, pylint / mypy will complain about call sites accessing these config
    variables.
    """
    default_keys = set(f.name for f in fields(Config()))
    configured_keys = set(raw_config.keys())
    custom_keys = configured_keys - default_keys
    if not custom_keys:
        cls: type = Config
    else:
        cls = make_dataclass(
            "ExtendedConfig",
            fields=[
                (k, object, field(default_factory=partial(raw_config.__getitem__, k)))
                for k in custom_keys
            ],
            bases=(Config,),
        )

    return cls(**raw_config)


def execute_post_config_load_hooks() -> None:
    for func in _post_config_load_hooks:
        func()


_post_config_load_hooks: List[Callable[[], None]] = []


def register_post_config_load_hook(func: Callable[[], None]) -> None:
    _post_config_load_hooks.append(func)


def get_default_config() -> Dict[str, Any]:
    default_config = asdict(Config())  # First apply the builtin config
    default_config.update(_get_default_config_from_legacy_plugins())
    default_config.update(_get_default_config_from_module_plugins())
    return default_config


def _get_default_config_from_legacy_plugins() -> Dict[str, Any]:
    """Plugins from local/share/check_mk/web/plugins/config are loaded here"""
    default_config: Dict[str, Any] = {}
    utils.load_web_plugins("config", default_config)
    return default_config


def _get_default_config_from_module_plugins() -> Dict[str, Any]:
    """Plugins from the config plugin package are loaded here

    These are `cmk.gui.plugins.config`, `cmk.gui.cee.plugins.config` and
    `cmk.gui.cme.plugins.config`.
    """
    config_plugin_vars: Dict = {}
    for module in _config_plugin_modules():
        config_plugin_vars.update(module.__dict__)

    default_config: Dict[str, Any] = {}
    for k, v in config_plugin_vars.items():
        if k[0] == "_" or k in ("CREConfig", "CEEConfig", "CMEConfig"):
            continue

        if isinstance(v, (dict, list)):
            v = copy.deepcopy(v)

        default_config[k] = v
    return default_config


def _config_plugin_modules() -> List[ModuleType]:
    return [
        module
        for name, module in sys.modules.items()
        if (
            name.startswith("cmk.gui.plugins.config.")  #
            or name.startswith("cmk.gui.cee.plugins.config.")  #
            or name.startswith("cmk.gui.cme.plugins.config.")
        )  #
        and name
        not in (
            "cmk.gui.plugins.config.base",  #
            "cmk.gui.cee.plugins.config.cee",  #
            "cmk.gui.cme.plugins.config.cme",
        )  #
        and module is not None
    ]


def prepare_raw_site_config(site_config: SiteConfigurations) -> SiteConfigurations:
    if not site_config:
        # Prevent problem when user has deleted all sites from his
        # configuration and sites is {}. We assume a default single site
        # configuration in that case.
        return default_single_site_configuration()
    return _migrate_old_site_config(site_config)


def _migrate_old_site_config(site_config: SiteConfigurations) -> SiteConfigurations:
    for site_id, site_cfg in site_config.items():
        # Until 1.6 "replication" could be not present or
        # set to "" instead of None
        if site_cfg.get("replication", "") == "":
            site_cfg["replication"] = None

        # Until 1.6 "url_prefix" was an optional attribute
        if "url_prefix" not in site_cfg:
            site_cfg["url_prefix"] = "/%s/" % site_id

        site_cfg.setdefault("proxy", None)

        _migrate_pre_16_socket_config(site_cfg)

    return site_config


# During development of the 1.6 version the site configuration has been cleaned up in several ways:
# 1. The "socket" attribute could be "disabled" to disable a site connection. This has already been
#    deprecated long time ago and was not configurable in WATO. This has now been superseded by
#    the dedicated "disabled" attribute.
# 2. The "socket" attribute was optional. A not present socket meant "connect to local unix" socket.
#    This is now replaced with a value like this ("local", None) to reflect the generic
#    CascadingDropdown() data structure of "(type, attributes)".
# 3. The "socket" attribute was stored in the livestatus.py socketurl encoded format, at least when
#    livestatus proxy was not used. This is now stored in the CascadingDropdown() native format and
#    converted here to the correct format.
# 4. When the livestatus proxy was enabled for a site, the settings were stored in the "socket"
#    attribute. The proxy settings were an additional dict which also held a "socket" key containing
#    the final socket connection properties.
#    This has now been split up. The top level socket settings are now used independent of the proxy.
#    The proxy options are stored in the separate key "proxy" which is a mandatory key.
def _migrate_pre_16_socket_config(site_cfg: Dict[str, Any]) -> None:
    socket = site_cfg.get("socket")
    if socket is None:
        site_cfg["socket"] = ("local", None)
        return

    if isinstance(socket, tuple) and socket[0] == "proxy":
        site_cfg["proxy"] = socket[1]

        # "socket" of proxy could either be None or two element tuple for "tcp"
        proxy_socket = site_cfg["proxy"].pop("socket", None)
        if proxy_socket is None:
            site_cfg["socket"] = ("local", None)

        elif isinstance(socket, tuple):
            site_cfg["socket"] = (
                "tcp",
                {
                    "address": proxy_socket,
                    "tls": ("plain_text", {}),
                },
            )

        else:
            raise NotImplementedError("Unhandled proxy socket: %r" % proxy_socket)

        return

    if socket == "disabled":
        site_cfg["disabled"] = True
        site_cfg["socket"] = ("local", None)
        return

    if isinstance(socket, str):
        site_cfg["socket"] = _migrate_string_encoded_socket(socket)


def _migrate_string_encoded_socket(value: str) -> Tuple[str, Union[Dict]]:
    family_txt, address = value.split(":", 1)

    if family_txt == "unix":
        return "unix", {
            "path": value.split(":", 1)[1],
        }

    if family_txt in ["tcp", "tcp6"]:
        host, port = address.rsplit(":", 1)
        return family_txt, {
            "address": (host, int(port)),
            "tls": ("plain_text", {}),
        }

    raise NotImplementedError()


def default_single_site_configuration() -> SiteConfigurations:
    return SiteConfigurations(
        {
            omd_site(): SiteConfiguration(
                {
                    "alias": _("Local site %s") % omd_site(),
                    "socket": ("local", None),
                    "disable_wato": True,
                    "disabled": False,
                    "insecure": False,
                    "url_prefix": url_prefix(),
                    "multisiteurl": "",
                    "persist": False,
                    "replicate_ec": False,
                    "replication": None,
                    "timeout": 5,
                    "user_login": True,
                    "proxy": None,
                }
            )
        }
    )
