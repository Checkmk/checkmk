#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import regex
import json
import re
import functools

from cmk.base.plugins.agent_based.utils.legacy_docker import (
    DeprecatedDict,
    DeprecatedList,
    legacy_map_keys as _legacy_map_keys,
)


def append_deprecation_warning(check_function):
    '''A wrapper to WARN if legacy code is used

    If the parse result is of one of the legacy Types the decorated
    check function will yield an additional WARNING state.

    These legacy parse results correspond to agents/plugins from version
    1.5.0b1 to 1.5.0p12
    '''
    @functools.wraps(check_function)
    def wrapper(item, params, parsed):

        is_deprecated = isinstance(parsed, (DeprecatedDict, DeprecatedList))
        catch_these = Exception if is_deprecated else ()

        try:
            results = check_function(item, params, parsed)
            if isinstance(results, tuple):
                yield results
            elif results is not None:
                for result in results:
                    yield result
        except catch_these:
            yield 3, "Could not handle data"
        finally:
            if is_deprecated:
                yield 1, ("Deprecated plugin/agent (see long output)(!)\n"
                          "You are using legacy code, which may lead to crashes and/or"
                          " incomplete information. Please upgrade the monitored host to"
                          " use the plugin 'mk_docker.py'.")

    return wrapper


def _legacy_docker_get_bytes(string):
    '''get number of bytes from string

    e.g.
    "123GB (42%)" -> 123000000000
    "0 B"         -> 0
    "2B"          -> 2
    "23 kB"       -> 23000
    '''
    # remove percent
    string = string.split('(')[0].strip()
    tmp = re.split('([a-zA-Z]+)', string)
    value_string = tmp[0].strip()
    unit_string = tmp[1].strip() if len(tmp) > 1 else 'B'
    try:
        factor = {
            'TB': 10**12,
            'GB': 10**9,
            'MB': 10**6,
            'KB': 10**3,
            'kB': 10**3,
            'B': 1,
            '': 1,
        }[unit_string]
        return int(float(value_string) * factor)
    except (ValueError, TypeError):
        return None


def _legacy_docker_trunk_id(hash_string):
    '''normalize to short ID

    Some docker commands use shortened, some long IDs:
    Convert long ones to short ones, e.g.
    "sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817"
    to
    "8b15606a9e3e"
    '''
    long_id = hash_string.split(':', 1)[-1]
    return long_id[:12]


def _legacy_docker_parse_table(rows, keys):
    '''docker provides us with space separated tables with field containing spaces

    e.g.:

    TYPE           TOTAL  ACTIVE   SIZE       RECLAIMABLE
    Images         7      6        2.076 GB   936.9 MB (45%)
    Containers     22     0        2.298 GB   2.298 GB (100%)
    Local Volumes  5      5        304 B      0 B (0%)
    '''
    if not rows or not rows[0]:
        return []

    indices = []
    for key in keys:
        field = key.upper()
        rex = regex(field + r'\ *')
        match = rex.search(rows[0][0])
        if match is not None:
            start, end = match.start(), match.end()
            if end - start == len(field):
                end = None
            indices.append((start, end))
        else:
            indices.append((0, 0))

    table = []
    for row in rows[1:]:
        if not row:
            continue
        try:
            line = {k: row[0][i:j].strip() for k, (i, j) in zip(keys, indices)}
        except IndexError:
            continue
        table.append(line)

    return table


def parse_legacy_docker_system_df(info):
    def int_or_zero(string):
        return int(string.strip() or 0)

    type_map = (
        ('type', 'total', 'active', 'size', 'reclaimable'),
        (str, int_or_zero, int_or_zero, _legacy_docker_get_bytes, _legacy_docker_get_bytes),
    )

    try:  # parse legacy json output: from 1.5.0 - 1.5.0p6
        table = [json.loads(",".join(row)) for row in info if row]
    except ValueError:
        table = _legacy_docker_parse_table(info, type_map[0])

    parsed = DeprecatedDict()
    for line in table:
        sane_line = {k.lower(): v for k, v in line.items()}
        _legacy_map_keys(sane_line, (('totalcount', 'total'),))
        for key, type_ in zip(type_map[0], type_map[1]):
            val = sane_line.get(key)
            if val is not None:
                sane_line[key] = type_(val)
        _legacy_map_keys(sane_line, (('total', 'count'),))
        parsed[sane_line.get("type").lower()] = sane_line

    return parsed


def _get_json_list(info):
    json_list = []
    for row in info:
        if not row:
            continue
        try:
            json_list.append(json.loads(' '.join(row)))
        except ValueError:
            pass
    # some buggy docker commands produce empty output
    return [element for element in json_list if element]


def parse_legacy_docker_subsection_images(info):

    table = _get_json_list(info)

    map_keys = (("ID", "Id"), ("CreatedAt", "Created"))

    parsed = DeprecatedDict()
    for item in table:
        _legacy_map_keys(item, map_keys)

        val = item.get("VirtualSize")
        if val is not None:
            item["VirtualSize"] = _legacy_docker_get_bytes(val)

        repotags = item.setdefault("RepoTags", [])
        if not repotags and item.get("Repository"):
            repotags.append('%s:%s' % (item["Repository"], item.get("Tag", "latest")))

        parsed[item.get("Id")] = item

    return parsed


def parse_legacy_docker_subsection_image_labels(info):

    table = _get_json_list(info)

    parsed = DeprecatedDict()
    for long_id, data in table:
        if data is not None:
            parsed[_legacy_docker_trunk_id(long_id)] = data
    return parsed


def parse_legacy_docker_subsection_image_inspect(info):
    parsed = DeprecatedDict()
    try:
        table = json.loads(' '.join(' '.join(row) for row in info if row))
    except ValueError:
        return parsed
    for image in table:
        parsed[_legacy_docker_trunk_id(image["Id"])] = image
    return parsed


def parse_legacy_docker_subsection_containers(info):

    table = _get_json_list(info)

    map_keys = (("ID", "Id"), ("CreatedAt", "Created"), ("Names", "Name"))

    parsed = DeprecatedDict()
    for item in table:
        _legacy_map_keys(item, map_keys)
        if "Status" in item:
            item["State"] = {"Status": item["Status"]}

        parsed[item.get("Id")] = item

    return parsed


def parse_legacy_docker_messed_up_labels(string):
    '''yield key value pairs

    'string' is in the format "key1=value1,key2=value2,...", but there
    may be unescaped commas in the values.
    '''
    def toggle_key_value():
        for chunk in string.split('='):
            for item in chunk.rsplit(',', 1):
                yield item

    toggler = toggle_key_value()
    return dict(zip(toggler, toggler))


def parse_legacy_docker_node_images(subsections):
    images = parse_legacy_docker_subsection_images(subsections.get("images", []))
    image_labels = parse_legacy_docker_subsection_image_labels(subsections.get("image_labels", []))
    image_inspect = parse_legacy_docker_subsection_image_inspect(
        subsections.get("image_inspect", []))
    containers = parse_legacy_docker_subsection_containers(subsections.get("containers", []))

    for image_id, pref_info in image_inspect.items():
        image = images.setdefault(image_id, {})
        image["Id"] = image_id
        labels = pref_info.get("Config", {}).get("Labels") or {}
        image.setdefault("Labels", {}).update(labels)
        image["Created"] = pref_info["Created"]
        image["VirtualSize"] = pref_info["VirtualSize"]

        repotags = pref_info.get("RepoTags")
        if repotags:
            image["RepoTags"] = repotags

        repodigests = pref_info.get("RepoDigests") or []
        if 'RepoDigest' in pref_info:
            # Singular? I think this was a bug, and never existed.
            # But better safe than sorry.
            repodigests.append(pref_info['RepoDigest'])
        image["RepoDigests"] = repodigests

    images_lookup = {}
    for image_id, image in images.items():
        image["amount_containers"] = 0
        image.setdefault("Labels", {})
        for reta in image.get("RepoTags", []):
            images_lookup[reta] = image
            images_lookup[_legacy_docker_trunk_id(image_id) + ':latest'] = image

    for image_id, labels in image_labels.items():
        image = images.get(_legacy_docker_trunk_id(image_id))
        if image is not None and labels is not None:
            image["Labels"].update(labels)

    for cont in containers.values():
        if 'Image' in cont:
            image_repotag = cont["Image"]
            if ':' not in image_repotag:
                image_repotag += ':latest'
            image = images_lookup.get(image_repotag)
            if image is not None:
                image["amount_containers"] += 1

        labels = cont.get("Labels")
        if isinstance(labels, (bytes, str)):  # TODO: Check if bytes is necessary
            cont["Labels"] = parse_legacy_docker_messed_up_labels(labels)

    return DeprecatedDict((("images", images), ("containers", containers)))


def parse_legacy_docker_container_node_name(info):
    try:
        return info[0][0]
    except IndexError:
        return None
