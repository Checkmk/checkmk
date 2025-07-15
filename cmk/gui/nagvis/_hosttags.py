#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.utils.paths
import cmk.utils.tags
from cmk.ccc import store
from cmk.utils.tags import TagConfigSpec

from ._php_formatter import format_php


def _export_hosttags_to_php(cfg: TagConfigSpec) -> None:
    """Make host tags available to NagVis

    Creates a includable PHP file which provides some functions which
    can be used by the calling program, for example NagVis. It declares
    the following API:

    taggroup_title(group_id)
    Returns the title of a Setup tag group

    taggroup_choice(group_id, list_of_object_tags)
    Returns either
      false: When taggroup does not exist in current config
      null:  When no choice can be found for the given taggroup
      array(tag, title): When a tag of the taggroup

    all_taggroup_choices(object_tags):
    Returns an array of elements which use the tag group id as key
    and have an assiciative array as value, where 'title' contains
    the tag group title and the value contains the value returned by
    taggroup_choice() for this tag group.
    """
    php_api_dir = cmk.utils.paths.var_dir / "wato/php-api"
    path = php_api_dir / "hosttags.php"
    php_api_dir.mkdir(mode=0o770, exist_ok=True, parents=True)

    tag_config = cmk.utils.tags.TagConfig.from_config(cfg)
    tag_config += cmk.utils.tags.BuiltinTagConfig()

    # Transform Setup internal data structures into easier usable ones
    hosttags_dict = {}
    for tag_group in tag_config.tag_groups:
        tags = {}
        for grouped_tag in tag_group.tags:
            tags[grouped_tag.id] = (grouped_tag.title, grouped_tag.aux_tag_ids)

        hosttags_dict[tag_group.id] = (tag_group.topic, tag_group.title, tags)

    auxtags_dict = dict(tag_config.aux_tag_list.get_choices())

    content = f"""<?php
// Created by WATO
global $mk_hosttags, $mk_auxtags;
$mk_hosttags = {format_php(hosttags_dict)};
$mk_auxtags = {format_php(auxtags_dict)};

function taggroup_title($group_id) {{
    global $mk_hosttags;
    if (isset($mk_hosttags[$group_id]))
        return $mk_hosttags[$group_id][0];
    else
        return $taggroup;
}}

function taggroup_choice($group_id, $object_tags) {{
    global $mk_hosttags;
    if (!isset($mk_hosttags[$group_id]))
        return false;
    foreach ($object_tags AS $tag) {{
        if (isset($mk_hosttags[$group_id][2][$tag])) {{
            // Found a match of the objects tags with the taggroup
            // now return an array of the matched tag and its alias
            return array($tag, $mk_hosttags[$group_id][2][$tag][0]);
        }}
    }}
    // no match found. Test whether or not a "None" choice is allowed
    if (isset($mk_hosttags[$group_id][2][null]))
        return array(null, $mk_hosttags[$group_id][2][null][0]);
    else
        return null; // no match found
}}

function all_taggroup_choices($object_tags) {{
    global $mk_hosttags;
    $choices = array();
    foreach ($mk_hosttags AS $group_id => $group) {{
        $choices[$group_id] = array(
            'topic' => $group[0],
            'title' => $group[1],
            'value' => taggroup_choice($group_id, $object_tags),
        );
    }}
    return $choices;
}}

?>
"""

    store.save_text_to_file(path, content)
