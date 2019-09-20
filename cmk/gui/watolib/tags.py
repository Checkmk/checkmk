#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
"""Helper functions for dealing with host tags"""

import os
import errno
from pathlib2 import Path
import six

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.i18n import _

import cmk.utils.tags
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import (
    multisite_dir,
    wato_root_dir,
)


class TagConfigFile(WatoSimpleConfigFile):
    """Handles loading the 1.6 tag definitions from GUI tags.mk or
    the pre 1.6 tag configuration from hosttags.mk

    When saving the configuration it also writes out the tags.mk for
    the cmk_base world.
    """
    def __init__(self):
        file_path = Path(multisite_dir()) / "tags.mk"
        super(TagConfigFile, self).__init__(config_file_path=file_path, config_variable="wato_tags")

    def _load_file(self, lock=False):
        if not self._config_file_path.exists():
            return self._load_pre_16_config(lock=lock)
        return super(TagConfigFile, self)._load_file(lock=lock)

    def _pre_16_hosttags_path(self):
        return Path(multisite_dir()).joinpath("hosttags.mk")

    def _load_pre_16_config(self, lock):
        legacy_cfg = store.load_mk_file(str(self._pre_16_hosttags_path()), {
            "wato_host_tags": [],
            "wato_aux_tags": []
        },
                                        lock=lock)

        _migrate_old_sample_config_tag_groups(legacy_cfg["wato_host_tags"],
                                              legacy_cfg["wato_aux_tags"])
        return cmk.utils.tags.transform_pre_16_tags(legacy_cfg["wato_host_tags"],
                                                    legacy_cfg["wato_aux_tags"])

    # TODO: Move the hosttag export to a hook
    def save(self, cfg):
        super(TagConfigFile, self).save(cfg)
        self._save_base_config(cfg)

        # Cleanup pre 1.6 config files (tags were just saved with new path)
        try:
            self._pre_16_hosttags_path().unlink()  # pylint: disable=no-member
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

        _export_hosttags_to_php(cfg)

    def _save_base_config(self, cfg):
        base_config_file = WatoSimpleConfigFile(config_file_path=Path(wato_root_dir()) / "tags.mk",
                                                config_variable="tag_config")
        base_config_file.save(cfg)


# Previous to 1.5 the "Agent type" tag group was created as sample config and was not
# a builtin tag group (which can not be modified by the user). With werk #5535 we changed
# the tag scheme and need to deal with the user config (which might extend the original tag group).
# Use two strategies:
#
# a) Check whether or not the tag group has been modified. If not, simply remove it from the user
#    config and use the builtin tag group in the future.
# b) Extend the tag group in the user configuration with the tag configuration we need for 1.5.
# TODO: Move to wato/watolib and register using register_post_config_load_hook()
def _migrate_old_sample_config_tag_groups(host_tags, aux_tags_):
    _remove_old_sample_config_tag_groups(host_tags, aux_tags_)
    _extend_user_modified_tag_groups(host_tags)


def _remove_old_sample_config_tag_groups(host_tags, aux_tags_):
    legacy_tag_group_default = (
        'agent',
        u'Agent type',
        [
            ('cmk-agent', u'Check_MK Agent (Server)', ['tcp']),
            ('snmp-only', u'SNMP (Networking device, Appliance)', ['snmp']),
            ('snmp-v1', u'Legacy SNMP device (using V1)', ['snmp']),
            ('snmp-tcp', u'Dual: Check_MK Agent + SNMP', ['snmp', 'tcp']),
            ('ping', u'No Agent', []),
        ],
    )

    try:
        host_tags.remove(legacy_tag_group_default)

        # Former tag choices (see above) are added as aux tags to allow the user to migrate
        # these tags and the objects that use them
        aux_tags_.insert(0,
                         ("snmp-only", "Data sources/Legacy: SNMP (Networking device, Appliance)"))
        aux_tags_.insert(0, ("snmp-tcp", "Data sources/Legacy: Dual: Check_MK Agent + SNMP"))
    except ValueError:
        pass  # Not there or modified

    legacy_aux_tag_ids = [
        'snmp',
        'tcp',
    ]

    for aux_tag in aux_tags_[:]:
        if aux_tag[0] in legacy_aux_tag_ids:
            aux_tags_.remove(aux_tag)


def _extend_user_modified_tag_groups(host_tags):
    """This method supports migration from <1.5 to 1.5 in case the user has a customized "Agent type" tag group
    See help of migrate_old_sample_config_tag_groups() and werk #5535 and #6446 for further information.

    Disclaimer: The host_tags data structure is a mess which will hopefully be cleaned up during 1.6 development.
    Basically host_tags is a list of configured tag groups. Each tag group is represented by a tuple like this:

    # tag_group_id, tag_group_title, tag_choices
    ('agent', u'Agent type',
        [
            # tag_id, tag_title, aux_tag_ids
            ('cmk-agent', u'Check_MK Agent (Server)', ['tcp']),
            ('snmp-only', u'SNMP (Networking device, Appliance)', ['snmp']),
            ('snmp-v1',   u'Legacy SNMP device (using V1)', ['snmp']),
            ('snmp-tcp',  u'Dual: Check_MK Agent + SNMP', ['snmp', 'tcp']),
            ('ping',      u'No Agent', []),
        ],
    )
    """
    tag_group = None
    for this_tag_group in host_tags:
        if this_tag_group[0] == "agent":
            tag_group = this_tag_group

    if tag_group is None:
        return  # Tag group does not exist

    # Mark all existing tag choices as legacy to help the user that this should be cleaned up
    for index, tag_choice in enumerate(tag_group[2][:]):
        if tag_choice[0] in ["no-agent", "special-agents", "all-agents", "cmk-agent"]:
            continue  # Don't prefix the standard choices

        if tag_choice[1].startswith("Legacy: "):
            continue  # Don't prefix already prefixed choices

        tag_choice_list = list(tag_choice)
        tag_choice_list[1] = "Legacy: %s" % tag_choice_list[1]
        tag_group[2][index] = tuple(tag_choice_list)

    tag_choices = [c[0] for c in tag_group[2]]

    if "no-agent" not in tag_choices:
        tag_group[2].insert(0, ("no-agent", _("No agent"), []))

    if "special-agents" not in tag_choices:
        tag_group[2].insert(
            0, ("special-agents", _("No Checkmk agent, all configured special agents"), ["tcp"]))

    if "all-agents" not in tag_choices:
        tag_group[2].insert(
            0, ("all-agents", _("Normal Checkmk agent, all configured special agents"), ["tcp"]))

    if "cmk-agent" not in tag_choices:
        tag_group[2].insert(
            0, ("cmk-agent", _("Normal Checkmk agent, or special agent if configured"), ["tcp"]))
    else:
        # Change title of cmk-agent tag choice and move to top
        for index, tag_choice in enumerate(tag_group[2]):
            if tag_choice[0] == "cmk-agent":
                tag_choice_list = list(tag_group[2].pop(index))
                tag_choice_list[1] = _("Normal Checkmk agent, or special agent if configured")
                tag_group[2].insert(0, tuple(tag_choice_list))
                break


# Creates a includable PHP file which provides some functions which
# can be used by the calling program, for example NagVis. It declares
# the following API:
#
# taggroup_title(group_id)
# Returns the title of a WATO tag group
#
# taggroup_choice(group_id, list_of_object_tags)
# Returns either
#   false: When taggroup does not exist in current config
#   null:  When no choice can be found for the given taggroup
#   array(tag, title): When a tag of the taggroup
#
# all_taggroup_choices(object_tags):
# Returns an array of elements which use the tag group id as key
# and have an assiciative array as value, where 'title' contains
# the tag group title and the value contains the value returned by
# taggroup_choice() for this tag group.
#
def _export_hosttags_to_php(cfg):
    php_api_dir = cmk.utils.paths.var_dir + "/wato/php-api/"
    path = php_api_dir + '/hosttags.php'
    store.mkdir(php_api_dir)

    tag_config = cmk.utils.tags.TagConfig()
    tag_config.parse_config(cfg)
    tag_config += cmk.utils.tags.BuiltinTagConfig()

    # need an extra lock file, since we move the auth.php.tmp file later
    # to auth.php. This move is needed for not having loaded incomplete
    # files into php.
    tempfile = path + '.tmp'
    lockfile = path + '.state'
    open(lockfile, 'a')
    store.aquire_lock(lockfile)

    # Transform WATO internal data structures into easier usable ones
    hosttags_dict = {}
    for tag_group in tag_config.tag_groups:
        tags = {}
        for grouped_tag in tag_group.tags:
            tags[grouped_tag.id] = (grouped_tag.title, grouped_tag.aux_tag_ids)

        hosttags_dict[tag_group.id] = (tag_group.topic, tag_group.title, tags)

    auxtags_dict = dict(tag_config.aux_tag_list.get_choices())

    # First write a temp file and then do a move to prevent syntax errors
    # when reading half written files during creating that new file
    open(tempfile, 'w').write('''<?php
// Created by WATO
global $mk_hosttags, $mk_auxtags;
$mk_hosttags = %s;
$mk_auxtags = %s;

function taggroup_title($group_id) {
    global $mk_hosttags;
    if (isset($mk_hosttags[$group_id]))
        return $mk_hosttags[$group_id][0];
    else
        return $taggroup;
}

function taggroup_choice($group_id, $object_tags) {
    global $mk_hosttags;
    if (!isset($mk_hosttags[$group_id]))
        return false;
    foreach ($object_tags AS $tag) {
        if (isset($mk_hosttags[$group_id][2][$tag])) {
            // Found a match of the objects tags with the taggroup
            // now return an array of the matched tag and its alias
            return array($tag, $mk_hosttags[$group_id][2][$tag][0]);
        }
    }
    // no match found. Test whether or not a "None" choice is allowed
    if (isset($mk_hosttags[$group_id][2][null]))
        return array(null, $mk_hosttags[$group_id][2][null][0]);
    else
        return null; // no match found
}

function all_taggroup_choices($object_tags) {
    global $mk_hosttags;
    $choices = array();
    foreach ($mk_hosttags AS $group_id => $group) {
        $choices[$group_id] = array(
            'topic' => $group[0],
            'title' => $group[1],
            'value' => taggroup_choice($group_id, $object_tags),
        );
    }
    return $choices;
}

?>
''' % (_format_php(hosttags_dict), _format_php(auxtags_dict)))
    # Now really replace the destination file
    os.rename(tempfile, path)
    store.release_lock(lockfile)
    os.unlink(lockfile)


def _format_php(data, lvl=1):
    s = ''
    if isinstance(data, (list, tuple)):
        s += 'array(\n'
        for item in data:
            s += '    ' * lvl + _format_php(item, lvl + 1) + ',\n'
        s += '    ' * (lvl - 1) + ')'
    elif isinstance(data, dict):
        s += 'array(\n'
        for key, val in data.iteritems():
            s += '    ' * lvl + _format_php(key, lvl + 1) + ' => ' + _format_php(val,
                                                                                 lvl + 1) + ',\n'
        s += '    ' * (lvl - 1) + ')'
    elif isinstance(data, str):
        s += '\'%s\'' % data.replace('\'', '\\\'')
    elif isinstance(data, six.text_type):
        s += '\'%s\'' % data.encode('utf-8').replace('\'', '\\\'')
    elif isinstance(data, bool):
        s += data and 'true' or 'false'
    elif data is None:
        s += 'null'
    else:
        s += str(data)

    return s
