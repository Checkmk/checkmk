#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, fields, make_dataclass
from functools import partial
from pathlib import Path
from types import ModuleType
from typing import Any, Final

import cmk.ccc.version as cmk_version

import cmk.utils.tags
from cmk.utils import paths

from cmk.gui import log, utils
from cmk.gui.ctx_stack import request_local_attr, set_global_var
from cmk.gui.exceptions import MKConfigError
from cmk.gui.i18n import _
from cmk.gui.plugins.config.base import CREConfig  # pylint: disable=cmk-module-layer-violation
from cmk.gui.type_defs import Key, RoleName

from cmk import trace

if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
    from cmk.gui.cee.plugins.config.cee import (  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation
        CEEConfig,
    )
else:
    # Stub needed for non enterprise edition
    class CEEConfig:  # type: ignore[no-redef]
        pass


if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CME:
    from cmk.gui.cme.config import (  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation
        CMEConfig,
    )
else:
    # Stub needed for non managed services edition
    class CMEConfig:  # type: ignore[no-redef]
        pass


tracer = trace.get_tracer()

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
default_authorized_builtin_role_ids: Final[list[RoleName]] = ["user", "admin", "guest"]
default_unauthorized_builtin_role_ids: Final[list[RoleName]] = [
    "agent_registration",
    "no_permissions",
]
builtin_role_ids: Final[list[RoleName]] = [
    *default_authorized_builtin_role_ids,
    *default_unauthorized_builtin_role_ids,
]


@dataclass
class Config(CREConfig, CEEConfig, CMEConfig):  # type: ignore[misc, unused-ignore]
    """Holds the loaded configuration during GUI processing

    The loaded configuration is then accessible through `from cmk.gui.globals import config`.
    For built-in config variables type checking and code completion works.

    This class is extended by `load_config` to support custom config variables which may
    be introduced by 3rd party extensions. For these variables we don't have the features
    mentioned above. But that's fine for now.
    """

    tags: cmk.utils.tags.TagConfig = cmk.utils.tags.TagConfig()


active_config = request_local_attr("config", Config)


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


def _determine_pysaml2_log_level(log_levels: Mapping[str, int]) -> Mapping[str, int]:
    """Note this sets the log level for the pysaml2 client, an external
    dependency used by SAML.

    The SAML log level is missing in the CRE editions, and at the time when
    cmk-update-config is run after an update from Checmk version 2.1.

    The log level of the pysaml2 package should be set to debug if the
    logging for SAML has been set to debug in the global settings. Otherwise it
    should be kept to a minimum as it spams the web.log

    >>> _determine_pysaml2_log_level({"cmk.web.saml2": 30})
    {'saml2': 50}
    >>> _determine_pysaml2_log_level({"cmk.web.saml2": 10})
    {'saml2': 10}
    >>> _determine_pysaml2_log_level({})
    {}

    """
    match log_levels.get("cmk.web.saml2"):
        case None:
            return {}
        case 10:
            return {"saml2": 10}
        case _:
            return {"saml2": 50}


@tracer.instrument("config.initialize")
def initialize() -> None:
    load_config()
    log_levels = {
        **active_config.log_levels,
        **_determine_pysaml2_log_level(active_config.log_levels),
    }
    log.set_log_levels(log_levels)
    cmk.gui.i18n.set_user_localizations(active_config.user_localizations)


def _load_config_file_to(path: str, raw_config: dict[str, Any]) -> None:
    """Load the given GUI configuration file"""
    try:
        with Path(path).open("rb") as f:
            exec(compile(f.read(), path, "exec"), {}, raw_config)  # nosec B102 # BNS:aee528
    except FileNotFoundError:
        pass
    except Exception as e:
        raise MKConfigError(_("Cannot read configuration file %s: %s:") % (path, e))


# Load multisite.mk and all files in multisite.d/. This will happen
# for *each* HTTP request.
# FIXME: Optimize this to cache the config etc. until either the config files or plugins
# have changed. We could make this being cached for multiple requests just like the
# plug-ins of other modules. This may save significant time in case of small requests like
# the graph ajax page or similar.
def load_config() -> None:
    # Set default values for all user-changable configuration settings
    raw_config = get_default_config()

    # Load assorted experimental parameters if any
    experimental_config = cmk.utils.paths.make_experimental_config_file()
    if experimental_config.exists():
        _load_config_file_to(str(experimental_config), raw_config)

    # First load main file
    _load_config_file_to(str(cmk.utils.paths.default_config_dir / "multisite.mk"), raw_config)

    # Load also recursively all files below multisite.d
    conf_dir = cmk.utils.paths.default_config_dir / "multisite.d"
    filelist = []
    if os.path.isdir(conf_dir):
        for root, _directories, files in os.walk(conf_dir):
            for filename in files:
                if filename.endswith(".mk"):
                    filelist.append(root + "/" + filename)

    filelist.sort()
    for p in filelist:
        _load_config_file_to(p, raw_config)

    raw_config["tags"] = cmk.utils.tags.get_effective_tag_config(raw_config["wato_tags"])

    # TODO: Temporary local hack to transform the values to the correct type. This needs
    # to be done in make_config_object() in the next step.
    if "agent_signature_keys" in raw_config:
        raw_config["agent_signature_keys"] = {
            key_id: Key.model_validate(raw_key)
            for key_id, raw_key in raw_config["agent_signature_keys"].items()
        }

    # Make sure, built-in roles are present, even if not modified and saved with Setup.
    for br in builtin_role_ids:
        raw_config["roles"].setdefault(br, {})

    set_global_var("config", make_config_object(raw_config))
    execute_post_config_load_hooks()


def make_config_object(raw_config: dict[str, Any]) -> Config:
    """Create the runtime config object

    In case there are some custom extensions installed which introduce new config variables, we make
    us compatible by creating a dynamic class which makes the Config class accept the required
    values. Since it is dynamic, pylint / mypy will complain about call sites accessing these config
    variables.
    """
    default_keys = {f.name for f in fields(Config())}
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

    return cls(**raw_config)  # type: ignore[no-any-return]


def execute_post_config_load_hooks() -> None:
    for func in _post_config_load_hooks:
        func()


_post_config_load_hooks: list[Callable[[], None]] = []


def register_post_config_load_hook(func: Callable[[], None]) -> None:
    _post_config_load_hooks.append(func)


def get_default_config() -> dict[str, Any]:
    default_config = asdict(Config())  # First apply the built-in config
    default_config.update(_get_default_config_from_legacy_plugins())
    default_config.update(_get_default_config_from_module_plugins())
    return default_config


def _get_default_config_from_legacy_plugins() -> dict[str, Any]:
    """Plug-ins from local/share/check_mk/web/plugins/config are loaded here"""
    default_config: dict[str, Any] = {}
    utils.load_web_plugins("config", default_config)
    return default_config


def _get_default_config_from_module_plugins() -> dict[str, Any]:
    """Plug-ins from the config plug-in package are loaded here

    These are `cmk.gui.plugins.config`, `cmk.gui.cee.plugins.config` and
    `cmk.gui.cme.plugins.config`.
    """
    config_plugin_vars: dict = {}
    for module in _config_plugin_modules():
        config_plugin_vars.update(module.__dict__)

    default_config: dict[str, Any] = {}
    for k, v in config_plugin_vars.items():
        if k[0] == "_" or k in ("CREConfig", "CEEConfig", "CMEConfig"):
            continue

        if isinstance(v, dict | list):
            v = copy.deepcopy(v)

        default_config[k] = v
    return default_config


def _config_plugin_modules() -> list[ModuleType]:
    return [
        module
        for name, module in list(sys.modules.items())
        if (
            name.startswith("cmk.gui.plugins.config.")
            or name.startswith("cmk.gui.cee.plugins.config.")
            or name.startswith("cmk.gui.cme.plugins.config.")
        )
        and name
        not in (
            "cmk.gui.plugins.config.base",
            "cmk.gui.cee.plugins.config.cee",
            "cmk.gui.cme.plugins.config.cme",
        )
        and module is not None
    ]
