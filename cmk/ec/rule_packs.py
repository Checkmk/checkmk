#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Utility module for common code between the Event Console and other parts
of Check_MK. The GUI is e.g. accessing this module for gathering the default
configuration.
"""

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
from cmk.utils import store

from .config import (
    ConfigFromWATO,
    ECRulePack,
    ECRulePackSpec,
    MkpRulePackBindingError,
    MkpRulePackProxy,
)
from .defaults import default_config, default_rule_pack
from .settings import Settings
from .settings import settings as create_settings


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
        """
        Returns the type of rule pack for a given rule pack ID to MKP mapping.
        """
        is_proxy = isinstance(rule_pack, MkpRulePackProxy)
        is_packaged = id_to_mkp.get(rule_pack.get("id")) is not None

        if not is_proxy and not is_packaged:
            return RulePackType.internal
        if is_proxy and not is_packaged:
            return RulePackType.exported
        if is_proxy and is_packaged:
            return RulePackType.unmodified_mkp
        return RulePackType.modified_mkp


def _default_settings() -> Settings:
    """Returns default EC settings. This function should vanish in the long run!"""
    return create_settings(
        "", cmk.utils.paths.omd_root, Path(cmk.utils.paths.default_config_dir), [""]
    )


def rule_pack_dir() -> Path:
    """
    Returns the default WATO directory of the Event Console.
    """
    return _default_settings().paths.rule_pack_dir.value


def mkp_rule_pack_dir() -> Path:
    """
    Returns the default directory for rule pack exports of the
    Event Console.
    """
    return _default_settings().paths.mkp_rule_pack_dir.value


def active_config_dir() -> Path:
    """Returns the directory where active rule packs of the Event Console are located."""
    return _default_settings().paths.active_config_dir.value


def remove_exported_rule_pack(id_: str) -> None:
    """
    Removes the .mk file representing the exported rule pack.
    """
    export_file = mkp_rule_pack_dir() / f"{id_}.mk"
    export_file.unlink()


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
def _load_config(  # pylint: disable=too-many-branches
    settings: Settings,
    config_files: Iterable[Path],
    *,
    apply_binding: bool,
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

    if apply_binding:
        # We need to have the choice to not bind the proxies, e.g. when
        # uninstalling packaged rule packs.
        # I think a better design would be to create instances of `BoundProxy` and `UnboundProxy`,
        # forcing the caller to deal with unbound proxies as they see fit.
        _bind_to_rule_pack_proxies(global_context["rule_packs"], global_context["mkp_rule_packs"])

    global_context.pop("mkp_rule_packs", None)
    global_context.pop("MkpRulePackProxy", None)
    config = cast(ConfigFromWATO, global_context)

    # Convert livetime fields in rules into new format
    for rule in config["rules"]:
        if "livetime" in rule:
            livetime = rule["livetime"]
            if not isinstance(livetime, tuple):
                rule["livetime"] = (livetime, ["open"])

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
                rule["contact_groups"] = {
                    "groups": rule["contact_groups"],
                    "notify": False,
                    "precedence": "host",
                }
            # Old configs only have a naked service level without a precedence.
            if isinstance(rule["sl"], int):
                rule["sl"] = {"value": rule["sl"], "precedence": "message"}

    # Convert old logging configurations
    levels = config["log_level"]
    if isinstance(levels, int):
        level = logging.INFO if levels == 0 else cmk.utils.log.VERBOSE
        levels = {
            "cmk.mkeventd": level,
            "cmk.mkeventd.EventServer": level,
            "cmk.mkeventd.EventStatus": level,
            "cmk.mkeventd.StatusServer": level,
            "cmk.mkeventd.lock": level,
        }
    if "cmk.mkeventd.lock" not in levels:
        levels["cmk.mkeventd.lock"] = levels["cmk.mkeventd"]
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
def load_config(settings: Settings, apply_binding: bool = True) -> ConfigFromWATO:
    """WATO needs all configured rule packs and other stuff - especially the central site in
    distributed setups."""
    return _load_config(
        settings,
        (
            [settings.paths.main_config_file.value]
            + sorted(settings.paths.config_dir.value.glob("**/*.mk"))
        ),
        apply_binding=apply_binding,
    )


# Used only by ourselves in by cmk.ec.main.load_configuration()
def load_active_config(settings: Settings) -> ConfigFromWATO:
    """The EC itself only uses (active) rule packs from the active config dir. Active rule packs
    are filtered rule packs, especially in distributed managed setups."""
    return _load_config(
        settings,
        sorted(settings.paths.active_config_dir.value.glob("**/*.mk")),
        apply_binding=True,
    )


# TODO: GUI stuff, used only in cmk.gui.mkeventd.helpers.save_active_config()
def save_active_config(
    settings: Settings,
    rule_packs: Iterable[ECRulePackSpec],
    pretty_print: bool = False,
) -> None:
    """
    Copy main configuration file from
        etc/check_mk/mkeventd.mk
    to
        var/mkeventd/active_config/mkeventd.mk

    Copy all config files recursively from
        etc/check_mk/mkeventd.d
    to
        var/mkeventd/active_config/conf.d

    The rules.mk is handled separately: save filtered rule_packs; see werk 16012.
    """
    try:
        shutil.rmtree(str(settings.paths.active_config_dir.value))
    except FileNotFoundError:
        pass

    settings.paths.active_config_dir.value.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy(
            settings.paths.main_config_file.value,
            settings.paths.active_config_dir.value / "mkeventd.mk",
        )
    except FileNotFoundError:
        pass

    active_conf_d = settings.paths.active_config_dir.value / "conf.d"
    for path in settings.paths.config_dir.value.glob("**/*.mk"):
        target = active_conf_d / path.relative_to(settings.paths.config_dir.value)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.name == "rules.mk":
            save_rule_packs(rule_packs, pretty_print=pretty_print, dir_=target.parent)
        else:
            shutil.copy(path, target)


def load_rule_packs(apply_binding: bool = True) -> Sequence[ECRulePack]:
    """Returns all rule packs (including MKP rule packs) of a site. Proxy objects
    in the rule packs are already bound to the referenced object."""
    return load_config(_default_settings(), apply_binding=apply_binding)["rule_packs"]


def save_rule_packs(
    rule_packs: Iterable[ECRulePack],
    pretty_print: bool = False,
    dir_: Path | None = None,
) -> None:
    """Saves the given rule packs to rules.mk. By default they are saved to the
    default directory for rule packs. If dir_ is given it is used instead of
    the default."""
    output = "# Written by WATO\n# encoding: utf-8\n\n"

    if pretty_print:
        rule_packs_text = pprint.pformat(list(rule_packs))
    else:
        rule_packs_text = repr(list(rule_packs))

    output += f"rule_packs += \\\n{rule_packs_text}\n"

    if not dir_:
        dir_ = rule_pack_dir()
    dir_.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(dir_ / "rules.mk", output)


# NOTE: It is essential that export_rule_pack() is called *before*
# save_rule_packs(), otherwise there is a race condition when the EC
# recursively reads all *.mk files!
def export_rule_pack(
    rule_pack: ECRulePack, pretty_print: bool = False, dir_: Path | None = None
) -> None:
    """
    Export the representation of a rule pack (i.e. a dict) to a .mk
    file accessible by the WATO module Extension Packages. In case
    of a MkpRulePackProxy the representation of the underlying rule
    pack is used.
    The name of the .mk file is determined by the ID of the rule pack,
    i.e. the rule pack 'test' will be saved as 'test.mk'
    By default the rule pack is saved to the default directory for
    mkp rule packs. If dir_ is given the default is replaced by the
    directory dir_.
    """
    if isinstance(rule_pack, MkpRulePackProxy):
        if rule_pack.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        rule_pack = rule_pack.rule_pack
    repr_ = pprint.pformat(rule_pack) if pretty_print else repr(rule_pack)
    output = f"""# Written by WATO
# encoding: utf-8

mkp_rule_packs['{rule_pack['id']}'] = \\
{repr_}
"""
    if not dir_:
        dir_ = mkp_rule_pack_dir()
    dir_.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(dir_ / f"{rule_pack['id']}.mk", output)


def install_packaged_rule_packs(file_names: Iterable[Path]) -> None:
    """
    Adds rule pack proxy objects to the list of rule packs given a list
    of file names. The file names without the file extension are used as
    the ID of the rule pack.
    """
    rule_packs = list(
        load_rule_packs(
            # Do not bind proxies when loading rule packs here.
            # We expect it should be possible, but let's not needlessly fail in case something else is awry.
            apply_binding=False,
        )
    )
    rule_pack_ids = {rp["id"]: i for i, rp in enumerate(rule_packs)}
    ids = [fn.stem for fn in file_names]
    for id_ in ids:
        index = rule_pack_ids.get(id_)
        if index is not None and isinstance(rule_packs[index], MkpRulePackProxy):
            rule_packs[index] = MkpRulePackProxy(id_)
        else:
            rule_packs.append(MkpRulePackProxy(id_))
    save_rule_packs(rule_packs)


def override_rule_pack_proxy(rule_pack_nr: int, rule_packs: list[ECRulePack]) -> None:
    """
    Replaces a MkpRulePackProxy by a working copy of the underlying rule pack.
    """
    proxy = rule_packs[rule_pack_nr]
    if not isinstance(proxy, MkpRulePackProxy):
        raise TypeError(
            f"Expected an instance of {MkpRulePackProxy.__name__} got {proxy.__class__.__name__}"
        )
    assert proxy.rule_pack is not None
    rule_packs[rule_pack_nr] = copy.deepcopy(proxy.rule_pack)


def release_packaged_rule_packs(file_names: Iterable[Path]) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the rule packs
    packaged in a MKP upon release of that MKP. The following cases have
    to be distinguished:

        1. Upon release of an unmodified MKP package the proxy in rules.mk
           and the exported rule pack are unchanged.
        2. Upon release of a MKP package with locally modified rule packs the
           modified rule pack updates the exported version.
    """
    rule_packs = list(
        load_rule_packs(
            # Do not bind proxies when loading rule packs here.
            # We expect it should be possible, but let's not needlessly fail in case something else is awry.
            apply_binding=False,
        )
    )
    rule_pack_ids = [rp["id"] for rp in rule_packs]
    affected_ids = [fn.stem for fn in file_names]

    save = False
    for id_ in affected_ids:
        index = rule_pack_ids.index(id_)
        rp = rule_packs[index]
        if not isinstance(rp, MkpRulePackProxy):
            save = True
            export_rule_pack(rp)
            rule_packs[index] = MkpRulePackProxy(id_)

    if save:
        save_rule_packs(rule_packs)


def uninstall_packaged_rule_packs(file_names: Iterable[Path]) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the packaged rule packs
    of a MKP upon deletion of that MKP. When a modified or an unmodified MKP is
    deleted the exported rule pack and the rule pack in rules.mk are both deleted.
    """
    affected_ids = {fn.stem for fn in file_names}
    save_rule_packs(
        # Do not try to bind the proxies.
        # We're calling this to drop the onces we can't bind anymore.
        rp
        for rp in load_rule_packs(apply_binding=False)
        if rp["id"] not in affected_ids
    )
