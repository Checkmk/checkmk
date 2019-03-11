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

import re
import os

import cmk.utils.paths
import cmk.utils.store as store

import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.watolib.utils import wato_fileheader
from cmk.gui.watolib.utils import (
    format_config_value,
    multisite_dir,
)


def parse_hosttag_title(title):
    if '/' in title:
        return title.split('/', 1)
    return None, title


def is_builtin_host_tag_group(tag_group_id):
    # Special handling for the agent tag group. It was a tag group created with
    # the sample WATO configuration until version 1.5x. This means users could've
    # customized the group. In case we find such a customization we treat it as
    # not builtin tag group.
    if tag_group_id == "agent":
        for tag_group in config.wato_host_tags:
            if tag_group[0] == tag_group_id:
                return False
        return True

    for tag_group in config.BuiltinTags().host_tags():
        if tag_group[0] == tag_group_id:
            return True
    return False


def is_builtin_aux_tag(taggroup_id):
    for builtin_taggroup in config.BuiltinTags().aux_tags():
        if builtin_taggroup[0] == taggroup_id:
            return True
    return False


def group_hosttags_by_topic(hosttags):
    tags = {}
    for entry in hosttags:
        topic, title = parse_hosttag_title(entry[1])
        if not topic:
            topic = _('Host tags')
        tags.setdefault(topic, [])
        tags[topic].append((entry[0], title) + entry[2:])
    return sorted(tags.items(), key=lambda x: x[0])


class Hosttag(object):
    def __init__(self):
        super(Hosttag, self).__init__()
        self._initialize()

    def _initialize(self):
        self.id = None
        self.title = None

    def validate(self):
        if not self.id:
            raise MKUserError("tag_id", _("Please specify a tag ID"))

        _validate_tag_id(self.id, "tag_id")

        if not self.title:
            raise MKUserError("title", _("Please supply a title for you auxiliary tag."))

    def parse_config(self, data):
        self._initialize()
        if isinstance(data, dict):
            self._parse_from_dict(data)
        else:
            self._parse_legacy_format(data)

    def _parse_from_dict(self, tag_info):
        self.id = tag_info["id"]
        self.title = tag_info["title"]

    def _parse_legacy_format(self, tag_info):
        self.id, self.title = tag_info[:2]


class AuxTag(Hosttag):
    def __init__(self, data=None):
        super(AuxTag, self).__init__()
        self.topic = None
        if data:
            self.parse_config(data)

    def _parse_from_dict(self, tag_info):
        super(AuxTag, self)._parse_from_dict(tag_info)
        if "topic" in tag_info:
            self.topic = tag_info["topic"]

    def _parse_legacy_format(self, tag_info):
        super(AuxTag, self)._parse_legacy_format(tag_info)
        self.topic, self.title = HosttagsConfiguration.parse_hosttag_title(self.title)

    def get_legacy_format(self):
        return self.id, HosttagsConfiguration.get_merged_topic_and_title(self)

    def get_dict_format(self):
        response = {"id": self.id, "title": self.title}
        if self.topic:
            response["topic"] = self.topic
        return response


class AuxtagList(object):
    def __init__(self):
        self._tags = []

    def get_tags(self):
        return self._tags

    def get_number(self, number):
        return self._tags[number]

    def append(self, aux_tag):
        if is_builtin_aux_tag(aux_tag.id):
            raise MKUserError("tag_id", _("You can not override a builtin auxiliary tag."))
        self._append(aux_tag)

    def _append(self, aux_tag):
        if self.has_aux_tag(aux_tag):
            raise MKUserError("tag_id",
                              _("This tag id does already exist in the list "
                                "of auxiliary tags."))
        self._tags.append(aux_tag)

    def update(self, position, aux_tag):
        self._tags[position] = aux_tag

    def validate(self):
        seen = set()
        for aux_tag in self._tags:
            aux_tag.validate()
            if aux_tag.id in seen:
                raise MKUserError("tag_id", _("Duplicate tag id in auxilary tags: %s") % aux_tag.id)
            seen.add(aux_tag.id)

    def has_aux_tag(self, aux_tag):
        for tmp_aux_tag in self._tags:
            if aux_tag.id == tmp_aux_tag.id:
                return True
        return False

    def get_tag_ids(self):
        return {tag.id for tag in self._tags}

    def get_legacy_format(self):
        response = []
        for aux_tag in self._tags:
            response.append(aux_tag.get_legacy_format())
        return response

    def get_dict_format(self):
        response = []
        for tag in self._tags:
            response.append(tag.get_dict_format())
        return response


class BuiltinAuxtagList(AuxtagList):
    def append(self, aux_tag):
        self._append(aux_tag)


class GroupedHosttag(Hosttag):
    def __init__(self, data=None):
        super(GroupedHosttag, self).__init__()
        self.aux_tag_ids = []
        self.parse_config(data)

    def _parse_from_dict(self, tag_info):
        super(GroupedHosttag, self)._parse_from_dict(tag_info)
        self.aux_tag_ids = tag_info["aux_tags"]

    def _parse_legacy_format(self, tag_info):
        super(GroupedHosttag, self)._parse_legacy_format(tag_info)

        if len(tag_info) == 3:
            self.aux_tag_ids = tag_info[2]

    def get_legacy_format(self):
        return self.id, self.title, self.aux_tag_ids

    def get_dict_format(self):
        return {"id": self.id, "title": self.title, "aux_tags": self.aux_tag_ids}


class HosttagGroup(object):
    def __init__(self, data=None):
        super(HosttagGroup, self).__init__()
        self._initialize()

        if data:
            if isinstance(data, dict):
                self._parse_from_dict(data)
            else:  # legacy tuple
                self._parse_legacy_format(data)

    def _initialize(self):
        self.id = None
        self.title = None
        self.topic = None
        self.tags = []

    def _parse_from_dict(self, group_info):
        self._initialize()
        self.id = group_info["id"]
        self.title = group_info["title"]
        self.topic = group_info.get("topic")
        self.tags = [GroupedHosttag(tag) for tag in group_info["tags"]]

    def _parse_legacy_format(self, group_info):
        self._initialize()
        group_id, group_title, tag_list = group_info[:3]

        self.id = group_id
        self.topic, self.title = HosttagsConfiguration.parse_hosttag_title(group_title)

        for tag in tag_list:
            self.tags.append(GroupedHosttag(tag))

    def get_tag_ids(self):
        return {tag.id for tag in self.tags}

    def get_dict_format(self):
        response = {"id": self.id, "title": self.title, "tags": []}
        if self.topic:
            response["topic"] = self.topic

        for tag in self.tags:
            response["tags"].append(tag.get_dict_format())

        return response

    def get_legacy_format(self):
        return self.id,\
               HosttagsConfiguration.get_merged_topic_and_title(self),\
               self.get_tags_legacy_format()

    def get_tags_legacy_format(self):
        response = []
        for tag in self.tags:
            response.append(tag.get_legacy_format())
        return response

    def get_tag_choices(self):
        choices = []
        for tag in self.tags:
            choices.append((tag.id, tag.title))
        return choices


class HosttagsConfiguration(object):
    def __init__(self):
        super(HosttagsConfiguration, self).__init__()
        self._initialize()

    def _initialize(self):
        self.tag_groups = []
        self.aux_tag_list = AuxtagList()

    @staticmethod
    def parse_hosttag_title(title):
        if '/' in title:
            return title.split('/', 1)
        return None, title

    @staticmethod
    def get_merged_topic_and_title(entity):
        if entity.topic:
            return "%s/%s" % (entity.topic, entity.title)
        return entity.title

    def get_hosttag_topics(self):
        names = set([])
        for tag_group in self.tag_groups:
            topic = tag_group.topic
            if topic:
                names.add((topic, topic))
        return list(names)

    def get_tag_group(self, tag_group_id):
        for group in self.tag_groups:
            if group.id == tag_group_id:
                return group

    def get_aux_tags(self):
        return self.aux_tag_list.get_tags()

    # Returns the raw ids of the grouped tags and the aux tags
    def get_tag_ids(self):
        response = set()
        for tag_group in self.tag_groups:
            response.update(tag_group.get_tag_ids())

        response.update(self.aux_tag_list.get_tag_ids())
        return response

    def get_tag_ids_with_group_prefix(self):
        response = set()
        for tag_group in self.tag_groups:
            response.update(["%s/%s" % (tag_group.id, tag) for tag in tag_group.get_tag_ids()])

        response.update(self.aux_tag_list.get_tag_ids())
        return response

    def parse_config(self, data):
        self._initialize()
        if isinstance(data, dict):
            self._parse_from_dict(data)
        else:
            self._parse_legacy_format(data[0], data[1])

        self.validate_config()

    def _parse_from_dict(self, tag_info):  # new style
        for tag_group in tag_info["tag_groups"]:
            self.tag_groups.append(HosttagGroup(tag_group))
        for aux_tag in tag_info["aux_tags"]:
            self.aux_tag_list.append(AuxTag(aux_tag))

    def _parse_legacy_format(self, taggroup_info, auxtags_info):  # legacy style
        for tag_group_tuple in taggroup_info:
            self.tag_groups.append(HosttagGroup(tag_group_tuple))

        for aux_tag_tuple in auxtags_info:
            self.aux_tag_list.append(AuxTag(aux_tag_tuple))

    def insert_tag_group(self, tag_group):
        if is_builtin_host_tag_group(tag_group.id):
            raise MKUserError("tag_id", _("You can not override a builtin tag group."))
        self._insert_tag_group(tag_group)

    def _insert_tag_group(self, tag_group):
        self.tag_groups.append(tag_group)
        self._validate_group(tag_group)

    def update_tag_group(self, tag_group):
        for idx, group in enumerate(self.tag_groups):
            if group.id == tag_group.id:
                self.tag_groups[idx] = tag_group
                break
        else:
            raise MKUserError("", _("Unknown tag group"))
        self._validate_group(tag_group)

    def validate_config(self):
        for tag_group in self.tag_groups:
            self._validate_group(tag_group)

        self.aux_tag_list.validate()

    # TODO: cleanup this mess
    # This validation is quite gui specific, I do not want to introduce this into the base classes
    def _validate_group(self, tag_group):
        if len(tag_group.id) == 0:
            raise MKUserError("tag_id", _("Please specify an ID for your tag group."))
        _validate_tag_id(tag_group.id, "tag_id")

        for tmp_group in self.tag_groups:
            if tmp_group == tag_group:
                continue
            if tmp_group.id == tag_group.id:
                raise MKUserError("tag_id", _("The tag group ID %s is already used by the tag group '%s'.") %\
                                    (tag_group.id, tmp_group.title))

        if not tag_group.title:
            raise MKUserError("title", _("Please specify a title for your host tag group."))

        have_none_tag = False
        for nr, tag in enumerate(tag_group.tags):
            if tag.id or tag.title:
                if not tag.id:
                    tag.id = None
                    if have_none_tag:
                        raise MKUserError("choices_%d_id" % (nr + 1),
                                          _("Only one tag may be empty."))
                    have_none_tag = True
                # Make sure tag ID is unique within this group
                for (n, x) in enumerate(tag_group.tags):
                    if n != nr and x.id == tag.id:
                        raise MKUserError(
                            "choices_id_%d" % (nr + 1),
                            _("Tags IDs must be unique. You've used <b>%s</b> twice.") % tag.id)

            if tag.id:
                # Make sure this ID is not used elsewhere
                for tmp_group in self.tag_groups:
                    # Do not compare the taggroup with itself
                    if tmp_group != tag_group:
                        for tmp_tag in tmp_group.tags:
                            # Check primary and secondary tags
                            if tag.id == tmp_tag.id:
                                raise MKUserError(
                                    "choices_id_%d" % (nr + 1),
                                    _("The tag ID '%s' is already being used by the choice "
                                      "'%s' in the tag group '%s'.") % (tag.id, tmp_tag.title,
                                                                        tmp_group.title))

                # Also check all defined aux tags even if they are not used anywhere
                for aux_tag in self.get_aux_tags():
                    if tag.id == aux_tag.id:
                        raise MKUserError(
                            "choices_id_%d" % (nr + 1),
                            _("The tag ID '%s' is already being used as auxiliary tag.") % tag.id)

        if len(tag_group.tags) == 0:
            raise MKUserError("id_0", _("Please specify at least one tag."))
        if len(tag_group.tags) == 1 and tag_group.tags[0] is None:
            raise MKUserError("id_0", _("Tags with only one choice must have an ID."))

    def load(self):
        hosttags, auxtags = self._load_hosttags()
        self._parse_legacy_format(hosttags, auxtags)

    # Current specification for hosttag entries: One tag definition is stored
    # as tuple of at least three elements. The elements are used as follows:
    # taggroup_id, group_title, list_of_choices, depends_on_tags, depends_on_roles, editable
    def _load_hosttags(self):
        default_config = {
            "wato_host_tags": [],
            "wato_aux_tags": [],
        }

        tag_config = cmk.utils.store.load_mk_file(multisite_dir() + "hosttags.mk", default_config)

        self._convert_manual_host_tags(tag_config["wato_host_tags"])
        config.migrate_old_sample_config_tag_groups(tag_config["wato_host_tags"],
                                                    tag_config["wato_aux_tags"])

        return tag_config["wato_host_tags"], tag_config["wato_aux_tags"]

    # Convert manually crafted host tags tags WATO-style. This
    # makes the migration easier
    def _convert_manual_host_tags(self, host_tags):
        for taggroup in host_tags:
            for nr, entry in enumerate(taggroup[2]):
                if len(entry) <= 2:
                    taggroup[2][nr] = entry + ([],)

    def save(self):
        self.validate_config()
        hosttags, auxtags = self.get_legacy_format()
        save_hosttags(hosttags, auxtags)

    def get_legacy_format(self):  # Convert new style to old style
        tag_groups_response = []
        for tag_group in self.tag_groups:
            tag_groups_response.append(tag_group.get_legacy_format())

        aux_tags_response = self.aux_tag_list.get_legacy_format()
        return tag_groups_response, aux_tags_response

    def get_dict_format(self):
        result = {"tag_groups": [], "aux_tags": []}
        for tag_group in self.tag_groups:
            result["tag_groups"].append(tag_group.get_dict_format())

        result["aux_tags"] = self.aux_tag_list.get_dict_format()

        return result


class BuiltinHosttagsConfiguration(HosttagsConfiguration):
    def _initialize(self):
        self.tag_groups = []
        self.aux_tag_list = BuiltinAuxtagList()

    def insert_tag_group(self, tag_group):
        self._insert_tag_group(tag_group)

    def load(self):
        builtin_tags = config.BuiltinTags()
        self._parse_legacy_format(builtin_tags.host_tags(), builtin_tags.aux_tags())


def save_hosttags(hosttags, auxtags):
    output = wato_fileheader()

    output += "wato_host_tags += \\\n%s\n\n" % format_config_value(hosttags)
    output += "wato_aux_tags += \\\n%s\n" % format_config_value(auxtags)

    store.mkdir(multisite_dir())
    store.save_file(multisite_dir() + "hosttags.mk", output)

    _export_hosttags_to_php(hosttags, auxtags)


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
def _export_hosttags_to_php(hosttags, auxtags):
    php_api_dir = cmk.utils.paths.var_dir + "/wato/php-api/"
    path = php_api_dir + '/hosttags.php'
    store.mkdir(php_api_dir)

    # need an extra lock file, since we move the auth.php.tmp file later
    # to auth.php. This move is needed for not having loaded incomplete
    # files into php.
    tempfile = path + '.tmp'
    lockfile = path + '.state'
    file(lockfile, 'a')
    store.aquire_lock(lockfile)

    # Transform WATO internal data structures into easier usable ones
    hosttags_dict = {}
    for entry in hosttags:
        id_, title, choices = entry[:3]
        tags = {}
        for tag_id, tag_title, tag_auxtags in choices:
            tags[tag_id] = tag_title, tag_auxtags
        topic, title = parse_hosttag_title(title)
        hosttags_dict[id_] = topic, title, tags
    auxtags_dict = dict(auxtags)

    # First write a temp file and then do a move to prevent syntax errors
    # when reading half written files during creating that new file
    file(tempfile, 'w').write('''<?php
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
    elif isinstance(data, unicode):
        s += '\'%s\'' % data.encode('utf-8').replace('\'', '\\\'')
    elif isinstance(data, bool):
        s += data and 'true' or 'false'
    elif data is None:
        s += 'null'
    else:
        s += str(data)

    return s


def _validate_tag_id(tag_id, varname):
    if not re.match("^[-a-z0-9A-Z_]*$", tag_id):
        raise MKUserError(
            varname, _("Invalid tag ID. Only the characters a-z, A-Z, "
                       "0-9, _ and - are allowed."))
