#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Utility module for common code between the Event Console and other parts
of Check_MK. The GUI is e.g. accessing this module for gathering the default
configuration.
"""

import contextlib
import copy
import logging
import pprint
import shutil
from collections.abc import Iterable, Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Any, cast

import cmk.utils.log
import cmk.utils.paths
from cmk.ccc import store

from .config import (
    ConfigFromWATO,
    ContactGroups,
    ECRulePack,
    ECRulePackSpec,
    LogConfig,
    MkpRulePackBindingError,
    MkpRulePackProxy,
    ServiceLevel,
)
from .defaults import default_config, default_rule_pack
from .settings import create_paths, Settings


class RulePackType(Enum):
    """
    A class to distinguish the four kinds of rule pack types:

        1. internal: A rule pack that is not available in the Extension Packages module.
        2. exported: A rule pack that is available in the Extension Packages, but not
                     yet part of a MKP.
        3. unmodified MKP: A rule pack that is packaged/provided in a MKP.
        4. modified MKP: A rule pack that was originally packaged/provided in a MKP but
                         was modified by a User and therefore replaced by a modified copy
                         of the rule pack.

    To get the type of a rule pack for an existing rule pack ID to
    MKP mapping the static method type_of can be used.
    """

    internal = "internal"
    exported = "exported"
    unmodified_mkp = "unmodified, packaged"
    modified_mkp = "modified, packaged"

    @staticmethod
    def type_of(rule_pack: ECRulePack, id_to_mkp: dict[Any, Any]) -> "RulePackType":
        """Returns the type of rule pack for a given rule pack ID to MKP mapping."""
        is_proxy = isinstance(rule_pack, MkpRulePackProxy)
        is_packaged = id_to_mkp.get(rule_pack.get("id")) is not None

        if not is_proxy and not is_packaged:
            return RulePackType.internal
        if is_proxy and not is_packaged:
            return RulePackType.exported
        if is_proxy and is_packaged:
            return RulePackType.unmodified_mkp
        return RulePackType.modified_mkp


def _exported_rule_pack_path(rule_pack: ECRulePack, path: Path) -> Path:
    return path / f"{rule_pack['id']}.mk"


def remove_exported_rule_pack(rule_pack: ECRulePack, path: Path) -> None:
    """Removes the .mk file representing the exported rule pack."""
    _exported_rule_pack_path(rule_pack, path).unlink()


def _bind_to_rule_pack_proxies(
    rule_packs: Iterable[ECRulePack], mkp_rule_packs: Mapping[str, ECRulePackSpec]
) -> None:
    """
    Binds all proxy rule packs of the variable rule_packs to
    the corresponding mkp_rule_packs.
    """
    for rule_pack in rule_packs:
        if isinstance(rule_pack, MkpRulePackProxy):
            if mkp_rule_pack := mkp_rule_packs.get(rule_pack.id_):
                rule_pack.bind_to(mkp_rule_pack)
            else:
                raise MkpRulePackBindingError(
                    f"Exported rule pack with ID '{rule_pack.id_}' not found."
                )


# Used by ourselves *and* the GUI!
def _load_config(
    config_files: Iterable[Path],
) -> ConfigFromWATO:
    """Load event console configuration."""
    # TODO: Do not use exec and the funny MkpRulePackProxy Kung Fu, removing the need for the copy/assert/cast below.
    global_context = dict(default_config())
    global_context["MkpRulePackProxy"] = MkpRulePackProxy
    global_context["mkp_rule_packs"] = {}
    for path in config_files:
        with open(str(path), mode="rb") as file_object:
            exec(compile(file_object.read(), path, "exec"), global_context)  # nosec B102 # BNS:aee528
    assert isinstance(global_context["rule_packs"], Iterable)
    assert isinstance(global_context["mkp_rule_packs"], Mapping)
    _bind_to_rule_pack_proxies(global_context["rule_packs"], global_context["mkp_rule_packs"])
    global_context.pop("mkp_rule_packs", None)
    global_context.pop("MkpRulePackProxy", None)
    config = cast(ConfigFromWATO, global_context)

    # Convert livetime fields in rules into new format
    for rule in config["rules"]:
        if "livetime" in rule:
            livetime = rule["livetime"]
            if not isinstance(livetime, tuple):  # TODO: Move this to upgrade time
                rule["livetime"] = (livetime, ["open"])  # type: ignore[unreachable]

    # Convert legacy rules into a default rule pack. Note that we completely
    # ignore legacy rules if there are rule packs already. It's a bit unclear
    # if we really want that, but at least that's how it worked in the past...
    if config["rules"] and not config["rule_packs"]:
        config["rule_packs"] = [default_rule_pack(config["rules"])]
    config["rules"] = []

    for rule_pack in config["rule_packs"]:
        for rule in rule_pack["rules"]:
            # Convert old contact_groups config
            if isinstance(rule.get("contact_groups"), list):
                rule["contact_groups"] = ContactGroups(
                    groups=rule["contact_groups"],
                    notify=False,
                    precedence="host",
                )
            # Old configs only have a naked service level without a precedence.
            if isinstance(rule["sl"], int):
                rule["sl"] = ServiceLevel(value=rule["sl"], precedence="message")

    # Convert old logging configurations
    levels: LogConfig = config["log_level"]
    if isinstance(levels, int):  # TODO: Move this to upgrade time
        level = logging.INFO if levels == 0 else cmk.utils.log.VERBOSE  # type: ignore[unreachable]
        levels = {
            "cmk.mkeventd": level,
            "cmk.mkeventd.EventServer": level,
            "cmk.mkeventd.EventStatus": level,
            "cmk.mkeventd.StatusServer": level,
            "cmk.mkeventd.lock": level,
        }
    if "cmk.mkeventd.lock" not in levels:  # TODO: Move this to upgrade time
        levels["cmk.mkeventd.lock"] = levels["cmk.mkeventd"]  # type: ignore[unreachable]
    config["log_level"] = levels

    # TODO: Move this up to avoid the need for casting?
    # Convert pre 1.4 hostname translation config
    translation = config["hostname_translation"]
    if isinstance(translation.get("regex"), tuple):
        translation["regex"] = [cast(tuple[str, str], translation.get("regex"))]

    if config.get("translate_snmptraps") is True:  # type: ignore[comparison-overlap]
        config["translate_snmptraps"] = (True, {})  # convert from pre-1.6.0 format

    return config


# TODO: GUI stuff, used only in cmk.gui.mkeventd.helpers.eventd_configuration()
def load_config() -> ConfigFromWATO:
    """WATO needs all configured rule packs and other stuff - especially the central site in
    distributed setups.
    """
    return _load_config(
        [cmk.utils.paths.ec_main_config_file]
        + sorted(cmk.utils.paths.ec_config_dir.glob("**/*.mk"))
    )


# Used only by ourselves in by cmk.ec.main.load_configuration()
def load_active_config(settings: Settings) -> ConfigFromWATO:
    """The EC itself only uses (active) rule packs from the active config dir. Active rule packs
    are filtered rule packs, especially in distributed managed setups.
    """
    return _load_config(sorted(settings.paths.active_config_dir.value.glob("**/*.mk")))


# TODO: GUI stuff, used only in cmk.gui.mkeventd.helpers.save_active_config()
def save_active_config(
    rule_packs: Iterable[ECRulePackSpec],
    pretty_print: bool = False,
) -> None:
    """
    Copy main configuration file from
        etc/check_mk/mkeventd.mk
    to
        var/mkeventd/active_config/mkeventd.mk.

    Copy all config files recursively from
        etc/check_mk/mkeventd.d
    to
        var/mkeventd/active_config/conf.d

    The rules.mk is handled separately: save filtered rule_packs; see werk 16012.
    """
    active_config_dir = create_paths(cmk.utils.paths.omd_root).active_config_dir.value
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(str(active_config_dir))

    active_config_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(FileNotFoundError):
        shutil.copy(
            cmk.utils.paths.ec_main_config_file,
            active_config_dir / "mkeventd.mk",
        )

    active_conf_d = active_config_dir / "conf.d"
    for path in cmk.utils.paths.ec_config_dir.glob("**/*.mk"):
        target = active_conf_d / path.relative_to(cmk.utils.paths.ec_config_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.name == "rules.mk":
            save_rule_packs(rule_packs, pretty_print=pretty_print, path=target.parent)
        else:
            shutil.copy(path, target)


def load_rule_packs() -> Sequence[ECRulePack]:
    """Returns all rule packs (including MKP rule packs) of a site. Proxy objects
    in the rule packs are already bound to the referenced object.
    """
    return load_config()["rule_packs"]


def save_rule_packs(rule_packs: Iterable[ECRulePack], pretty_print: bool, path: Path) -> None:
    """Saves the given rule packs to rules.mk."""
    output = "# Written by WATO\n# encoding: utf-8\n\n"

    rule_packs_text = pprint.pformat(list(rule_packs)) if pretty_print else repr(list(rule_packs))

    output += f"rule_packs += \\\n{rule_packs_text}\n"

    path.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(path / "rules.mk", output)


# NOTE: It is essential that export_rule_pack() is called *before*
# save_rule_packs(), otherwise there is a race condition when the EC
# recursively reads all *.mk files!
def export_rule_pack(rule_pack: ECRulePack, pretty_print: bool, path: Path) -> None:
    """
    Export the representation of a rule pack (i.e. a dict) to a .mk
    file accessible by the WATO module Extension Packages. In case
    of a MkpRulePackProxy the representation of the underlying rule
    pack is used.
    The name of the .mk file is determined by the ID of the rule pack,
    i.e. the rule pack 'test' will be saved as 'test.mk'.
    """
    if isinstance(rule_pack, MkpRulePackProxy):
        if rule_pack.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        rule_pack = rule_pack.rule_pack
    repr_ = pprint.pformat(rule_pack) if pretty_print else repr(rule_pack)
    output = f"""# Written by WATO
# encoding: utf-8

mkp_rule_packs['{rule_pack["id"]}'] = \\
{repr_}
"""
    path.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(_exported_rule_pack_path(rule_pack, path), output)


def override_rule_pack_proxy(rule_pack_nr: int, rule_packs: list[ECRulePack]) -> None:
    """Replaces a MkpRulePackProxy by a working copy of the underlying rule pack."""
    proxy = rule_packs[rule_pack_nr]
    if not isinstance(proxy, MkpRulePackProxy):
        raise TypeError(
            f"Expected an instance of {MkpRulePackProxy.__name__} got {proxy.__class__.__name__}"
        )
    assert proxy.rule_pack is not None
    rule_packs[rule_pack_nr] = copy.deepcopy(proxy.rule_pack)
