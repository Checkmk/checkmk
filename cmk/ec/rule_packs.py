#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Utility module for common code between the Event Console and other parts
of Check_MK. The GUI is e.g. accessing this module for gathering the default
configuration.
"""

import copy
import logging
import os
import pprint
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    cast,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Union,
)

import cmk.utils.log
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKException

from .config import ConfigFromWATO
from .defaults import default_config, default_rule_pack
from .settings import Settings
from .settings import settings as create_settings

ECRuleSpec = dict[str, Any]
ECRulePackSpec = dict[str, Any]  # TODO: improve this type
ECRulePack = Union[ECRulePackSpec, "MkpRulePackProxy"]


class MkpRulePackBindingError(MKException):
    """Base class for exceptions related to rule pack binding"""


class MkpRulePackProxy(MutableMapping[str, Any]):  # pylint: disable=too-many-ancestors
    """
    An object of this class represents an entry (i.e. a rule pack) in
    mkp_rule_packs. It is used as a reference to an EC rule pack
    that either can be exported or is already exported in a MKP.

    A newly created instance is not yet connected to a specific rule pack.
    This is achieved via the method bind_to.
    """

    def __init__(self, rule_pack_id: str) -> None:
        super().__init__()
        # Ideally the 'id_' would not be necessary and the proxy object would
        # be bound to it's referenced object upon initialization. Unfortunately,
        # this is not possible because the mknotifyd.mk could specify referenced
        # objects as well.
        self.id_ = rule_pack_id
        self.rule_pack: Optional[ECRulePackSpec] = None

    def __getitem__(self, key: str) -> Any:
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        return self.rule_pack[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        self.rule_pack[key] = value

    def __delitem__(self, key: str) -> None:
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        del self.rule_pack[key]

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self.id_}")'

    # __iter__ and __len__ are only defined as a workaround for a buggy entry
    # in the typeshed
    def __iter__(self) -> Iterator[str]:
        yield from self.keys()

    def __len__(self) -> int:
        return len(self.keys())

    def keys(self) -> KeysView[str]:
        """List of keys of this rule pack"""
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        return self.rule_pack.keys()

    def bind_to(self, mkp_rule_pack: ECRulePackSpec) -> None:
        """Binds this rule pack to the given MKP rule pack"""
        if self.id_ != mkp_rule_pack["id"]:
            raise MkpRulePackBindingError(
                f"The IDs of {self} and {mkp_rule_pack} cannot be different."
            )

        self.rule_pack = mkp_rule_pack

    @property
    def is_bound(self) -> bool:
        """Has this rule pack been bound via bind_to()?"""
        return self.rule_pack is not None


class RulePackType(Enum):  # pylint: disable=too-few-public-methods
    """
    A class to distinguishes the four kinds of rule pack types:

        1. internal: A rule pack that is not available in the Extension Packages module.
        2. exported: A rule pack that is available in the Extension Packages, but not
                     yet part of a MKP.
        3. unmodified MKP: A rule pack that is packaged/provided in a MKP.
        4. modified MKP: A rule pack that was orignially packaged/provided in a MKP but
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


def remove_exported_rule_pack(id_: str) -> None:
    """
    Removes the .mk file representing the exported rule pack.
    """
    export_file = mkp_rule_pack_dir() / ("%s.mk" % id_)
    export_file.unlink()


def _bind_to_rule_pack_proxies(
    rule_packs: Iterable[Any], mkp_rule_packs: Mapping[Any, Any]
) -> None:
    """
    Binds all proxy rule packs of the variable rule_packs to
    the corresponding mkp_rule_packs.
    """
    for rule_pack in rule_packs:
        try:
            if isinstance(rule_pack, MkpRulePackProxy):
                rule_pack.bind_to(mkp_rule_packs[rule_pack.id_])
        except KeyError:
            raise MkpRulePackBindingError(
                'Exported rule pack with ID "%s" not found.' % rule_pack.id_
            )


def load_config(settings: Settings) -> ConfigFromWATO:  # pylint: disable=too-many-branches
    """Load event console configuration."""
    # TODO: Do not use exec and the funny MkpRulePackProxy Kung Fu, removing the need for the two casts below.
    global_context = cast(dict[str, Any], default_config())
    global_context["MkpRulePackProxy"] = MkpRulePackProxy
    for path in [settings.paths.main_config_file.value] + sorted(
        settings.paths.config_dir.value.glob("**/*.mk")
    ):
        with open(str(path), mode="rb") as file_object:
            exec(file_object.read(), global_context)  # pylint: disable=exec-used
    global_context.pop("MkpRulePackProxy", None)
    config = cast(ConfigFromWATO, global_context)
    _bind_to_rule_pack_proxies(config["rule_packs"], config["mkp_rule_packs"])

    # Convert livetime fields in rules into new format
    for rule in config["rules"]:
        if "livetime" in rule:
            livetime = rule["livetime"]
            if not isinstance(livetime, tuple):
                rule["livetime"] = (livetime, ["open"])

    # Convert legacy rules into a default rule pack. Note that we completely
    # ignore legacy rules if there are rule packs alreday. It's a bit unclear
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


def load_rule_packs() -> Sequence[ECRulePackSpec]:
    """Returns all rule packs (including MKP rule packs) of a site. Proxy objects
    in the rule packs are already bound to the referenced object."""
    return load_config(_default_settings())["rule_packs"]


def save_rule_packs(
    rule_packs: Iterable[ECRulePack], pretty_print: bool = False, dir_: Optional[Path] = None
) -> None:
    """Saves the given rule packs to rules.mk. By default they are saved to the
    default directory for rule packs. If dir_ is given it is used instead of
    the default."""
    output = "# Written by WATO\n# encoding: utf-8\n\n"

    if pretty_print:
        rule_packs_text = pprint.pformat(rule_packs)
    else:
        rule_packs_text = repr(rule_packs)

    output += "rule_packs += \\\n%s\n" % rule_packs_text

    if not dir_:
        dir_ = rule_pack_dir()
    dir_.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(dir_ / "rules.mk", output)


# NOTE: It is essential that export_rule_pack() is called *before*
# save_rule_packs(), otherwise there is a race condition when the EC
# recursively reads all *.mk files!
def export_rule_pack(
    rule_pack: ECRulePack, pretty_print: bool = False, dir_: Optional[Path] = None
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
    output = (
        "# Written by WATO\n" "# encoding: utf-8\n" "\n" "mkp_rule_packs['%s'] = \\\n" "%s\n"
    ) % (rule_pack["id"], repr_)

    if not dir_:
        dir_ = mkp_rule_pack_dir()
    dir_.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(dir_ / ("%s.mk" % rule_pack["id"]), str(output))


def add_rule_pack_proxies(file_names: Iterable[str]) -> None:
    """
    Adds rule pack proxy objects to the list of rule packs given a list
    of file names. The file names without the file extension are used as
    the ID of the rule pack.
    """
    rule_packs: list[ECRulePack] = []
    rule_packs += load_rule_packs()
    rule_pack_ids = {rp["id"]: i for i, rp in enumerate(rule_packs)}
    ids = [os.path.splitext(fn)[0] for fn in file_names]
    for id_ in ids:
        index = rule_pack_ids.get(id_)
        if index is not None and isinstance(rule_packs[index], MkpRulePackProxy):
            rule_packs[index] = MkpRulePackProxy(id_)
        else:
            rule_packs.append(MkpRulePackProxy(id_))
    save_rule_packs(rule_packs)


def override_rule_pack_proxy(rule_pack_nr: str, rule_packs: dict[str, Any]) -> None:
    """
    Replaces a MkpRulePackProxy by a working copy of the underlying rule pack.
    """
    proxy = rule_packs[rule_pack_nr]
    if not isinstance(proxy, MkpRulePackProxy):
        raise TypeError(
            "Expected an instance of %s got %s"
            % (MkpRulePackProxy.__name__, proxy.__class__.__name__)
        )
    rule_packs[rule_pack_nr] = copy.deepcopy(proxy.rule_pack)


def release_packaged_rule_packs(file_names: Iterable[str]) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the rule packs
    packaged in a MKP upon release of that MKP. The following cases have
    to be distinguished:

        1. Upon release of an unmodified MKP package the proxy in rules.mk
           and the exported rule pack are unchanged.
        2. Upon release of a MKP package with locally modified rule packs the
           modified rule pack updates the exported version.
    """
    if not file_names:
        return

    rule_packs: list[ECRulePack] = []
    rule_packs += load_rule_packs()
    rule_pack_ids = [rp["id"] for rp in rule_packs]
    affected_ids = [os.path.splitext(fn)[0] for fn in file_names]

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
