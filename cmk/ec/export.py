#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""
Utility module for common code between the Event Console and other parts
of Check_MK. The GUI is e.g. accessing this module for gathering the default
configuration.
"""

import copy
from enum import Enum
import logging
import os
import pprint
from typing import Any, Dict, Iterable, List, Optional, Tuple  # pylint: disable=unused-import
import UserDict

from pathlib2 import Path

import cmk.utils.log
import cmk.utils.paths
import cmk.utils.store
import cmk.ec.defaults
import cmk.ec.settings


class MkpRulePackBindingError(Exception):
    """Base class for exceptions related to rule pack binding"""
    pass


class MkpRulePackProxy(UserDict.DictMixin):
    """
    An object of this class represents an entry (i.e. a rule pack) in
    mkp_rule_packs. It is used as a reference to an EC rule pack
    that either can be exported or is already exported in a MKP.

    A newly created instance is not yet connected to a specific rule pack.
    This is achieved via the method bind_to.
    """
    def __init__(self, rule_pack_id):
        # Ideally the 'id_' would not be necessary and the proxy object would
        # be bound to it's referenced object upon initialization. Unfortunately,
        # this is not possible because the mknotifyd.mk could specify referenced
        # objects as well.
        self.id_ = rule_pack_id  # type: str
        self.rule_pack = None  # type: Dict[str, Any]

    def __getitem__(self, key):
        return self.rule_pack[key]

    def __setitem__(self, key, value):
        self.rule_pack[key] = value

    def __delattr__(self, key):
        del self.rule_pack[key]

    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self.id_)

    # __iter__ and __len__ are only defined as a workaround for a buggy entry
    # in the typeshed
    def __iter__(self):
        for k in self.keys():
            yield k

    def __len__(self):
        return len(self.keys())

    def keys(self):
        # type: () -> List[str]
        """List of keys of this rule pack"""
        return self.rule_pack.keys()

    def bind_to(self, mkp_rule_pack):
        # type: (Dict[str, Any]) -> None
        """Binds this rule pack to the given MKP rule pack"""
        if self.id_ != mkp_rule_pack['id']:
            raise MkpRulePackBindingError('The IDs of %s and %s cannot be different.' %
                                          (self, mkp_rule_pack))

        self.rule_pack = mkp_rule_pack

    @property
    def is_bound(self):
        # type: () -> bool
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
    internal = 'internal'
    exported = 'exported'
    unmodified_mkp = 'unmodified, packaged'
    modified_mkp = 'modified, packaged'

    @staticmethod
    def type_of(rule_pack, id_to_mkp):
        # type: (Dict[str, Any], Dict[Any, Any]) -> RulePackType
        """
        Returns the type of rule pack for a given rule pack ID to MKP mapping.
        """
        is_proxy = isinstance(rule_pack, MkpRulePackProxy)
        is_packaged = id_to_mkp.get(rule_pack.get('id')) is not None

        if not is_proxy and not is_packaged:
            return RulePackType.internal
        if is_proxy and not is_packaged:
            return RulePackType.exported
        if is_proxy and is_packaged:
            return RulePackType.unmodified_mkp
        return RulePackType.modified_mkp


def _default_settings():
    # type: () -> cmk.ec.settings.Settings
    """Returns default EC settings. This function should vanish in the long run!"""
    return cmk.ec.settings.settings('', Path(cmk.utils.paths.omd_root),
                                    Path(cmk.utils.paths.default_config_dir), [''])


def rule_pack_dir():
    # type: () -> Path
    """
    Returns the default WATO directory of the Event Console.
    """
    return _default_settings().paths.rule_pack_dir.value


def mkp_rule_pack_dir():
    # type: () -> Path
    """
    Returns the default directory for rule pack exports of the
    Event Console.
    """
    return _default_settings().paths.mkp_rule_pack_dir.value


def remove_exported_rule_pack(id_):
    # type: (str) -> None
    """
    Removes the .mk file representing the exported rule pack.
    """
    export_file = mkp_rule_pack_dir() / ("%s.mk" % id_)
    export_file.unlink()


def _bind_to_rule_pack_proxies(rule_packs, mkp_rule_packs):
    # type: (Any, Any) -> None
    """
    Binds all proxy rule packs of the variable rule_packs to
    the corresponding mkp_rule_packs.
    """
    for rule_pack in rule_packs:
        try:
            if isinstance(rule_pack, MkpRulePackProxy):
                rule_pack.bind_to(mkp_rule_packs[rule_pack.id_])
        except KeyError:
            raise MkpRulePackBindingError('Exported rule pack with ID "%s" not found.' %
                                          rule_pack.id_)


def load_config(settings):
    # type: (cmk.ec.settings.Settings) -> Dict[str, Any]
    """Load event console configuration."""
    config = cmk.ec.defaults.default_config()
    config["MkpRulePackProxy"] = MkpRulePackProxy
    for path in [settings.paths.main_config_file.value] + \
            sorted(settings.paths.config_dir.value.glob('**/*.mk')):
        with open(str(path)) as file_object:
            exec (file_object, config)  # pylint: disable=exec-used
    config.pop("MkpRulePackProxy", None)
    _bind_to_rule_pack_proxies(config['rule_packs'], config['mkp_rule_packs'])

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
        config["rule_packs"] = [cmk.ec.defaults.default_rule_pack(config["rules"])]
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
            "cmk.mkeventd.lock": level
        }
    if "cmk.mkeventd.lock" not in levels:
        levels["cmk.mkeventd.lock"] = levels["cmk.mkeventd"]
    config["log_level"] = levels

    # Convert pre 1.4 hostname translation config
    translation = config["hostname_translation"]
    if "regex" in translation and not isinstance(translation["regex"], list):
        translation["regex"] = [translation["regex"]]

    return config


def load_rule_packs():
    # type: () -> Any
    """Returns all rule packs (including MKP rule packs) of a site. Proxy objects
    in the rule packs are already bound to the referenced object."""
    return load_config(_default_settings())["rule_packs"]


def save_rule_packs(rule_packs, pretty_print=False, dir_=None):
    # type: (List[Dict[str, Any]], bool, Optional[Path]) -> None
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
    cmk.utils.store.save_file(str(dir_ / "rules.mk"), output)


# NOTE: It is essential that export_rule_pack() is called *before*
# save_rule_packs(), otherwise there is a race condition when the EC
# recursively reads all *.mk files!
def export_rule_pack(rule_pack, pretty_print=False, dir_=None):
    # type: (Dict[str, Any], bool, Optional[Path]) -> None
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
        rule_pack = rule_pack.rule_pack

    repr_ = (pprint.pformat(rule_pack) if pretty_print else repr(rule_pack))
    output = ("# Written by WATO\n"
              "# encoding: utf-8\n"
              "\n"
              "mkp_rule_packs['%s'] = \\\n"
              "%s\n") % (rule_pack['id'], repr_)

    if not dir_:
        dir_ = mkp_rule_pack_dir()
    dir_.mkdir(parents=True, exist_ok=True)
    cmk.utils.store.save_file(str(dir_ / ("%s.mk" % rule_pack['id'])), output)


def add_rule_pack_proxies(file_names):
    # type: (Iterable[str]) -> None
    """
    Adds rule pack proxy objects to the list of rule packs given a list
    of file names. The file names without the file extension are used as
    the ID of the rule pack.
    """
    rule_packs = load_rule_packs()
    ids = [os.path.splitext(fn)[0] for fn in file_names]
    for id_ in ids:
        rule_packs.append(MkpRulePackProxy(id_))
    save_rule_packs(rule_packs)


def override_rule_pack_proxy(rule_pack_nr, rule_packs):
    # type: (str, Dict[str, Any]) -> None
    """
    Replaces a MkpRulePackProxy by a working copy of the underlying rule pack.
    """
    proxy = rule_packs[rule_pack_nr]
    if not isinstance(proxy, MkpRulePackProxy):
        raise TypeError('Expected an instance of %s got %s' %
                        (MkpRulePackProxy.__name__, proxy.__class__.__name__))
    rule_packs[rule_pack_nr] = copy.deepcopy(proxy.rule_pack)


def release_packaged_rule_packs(file_names):
    # type: (Iterable[str]) -> None
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

    rule_packs = load_rule_packs()
    rule_pack_ids = [rp['id'] for rp in rule_packs]
    affected_ids = [os.path.splitext(fn)[0] for fn in file_names]

    save = False
    for id_ in affected_ids:
        index = rule_pack_ids.index(id_)
        if not isinstance(rule_packs[index], MkpRulePackProxy):
            save = True
            export_rule_pack(rule_packs[index])
            rule_packs[index] = MkpRulePackProxy(id_)

    if save:
        save_rule_packs(rule_packs)


def remove_packaged_rule_packs(file_names, delete_export=True):
    # type: (Iterable[str], bool) -> None
    """
    This function synchronizes the rule packs in rules.mk and the packaged rule packs
    of a MKP upon deletion of that MKP. When a modified or an unmodified MKP is
    deleted the exported rule pack and the rule pack in rules.mk are both deleted.
    """
    if not file_names:
        return

    rule_packs = load_rule_packs()
    rule_pack_ids = [rp['id'] for rp in rule_packs]
    affected_ids = [os.path.splitext(fn)[0] for fn in file_names]

    for id_ in affected_ids:
        index = rule_pack_ids.index(id_)
        del rule_packs[index]
        if delete_export:
            remove_exported_rule_pack(id_)

    save_rule_packs(rule_packs)


def rule_pack_id_to_mkp(package_info):
    # type: (Any) -> Dict[str, Any]
    """
    Returns a dictionary of rule pack ID to MKP package for a given package_info.
    The package info has to be in the format defined by cmk_base/packaging.py.
    Every rule pack is contained exactly once in this mapping. If no corresponding
    MKP exists, the value of that mapping is None.
    """
    def mkp_of(rule_pack_file):
        # type: (str) -> Any
        """Find the MKP for the given file"""
        for mkp, content in package_info.get('installed', {}).iteritems():
            if rule_pack_file in content.get('files', {}).get('ec_rule_packs', []):
                return mkp
        return None

    exported_rule_packs = package_info['parts']['ec_rule_packs']['files']

    return {os.path.splitext(file_)[0]: mkp_of(file_) for file_ in exported_rule_packs}
