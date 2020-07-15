#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# *--encoding: UTF-8--*
# yapf: disable
import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("parsed, label_value_pairs", [
    ({}, [(u"cmk/docker_object", u"container")]),
    ({"ImageTags": []}, [(u"cmk/docker_object", u"container")]),
    ({"ImageTags": ["doctor:strange"]}, [
        (u"cmk/docker_object", u"container"),
        (u"cmk/docker_image", u"doctor:strange"),
        (u"cmk/docker_image_name", u"doctor"),
        (u"cmk/docker_image_version", u"strange"),
    ]),
    ({"ImageTags": ["fiction/doctor:strange"]}, [
        (u"cmk/docker_object", u"container"),
        (u"cmk/docker_image", u"fiction/doctor:strange"),
        (u"cmk/docker_image_name", u"doctor"),
        (u"cmk/docker_image_version", u"strange"),
    ]),
    ({"ImageTags": ["library:8080/fiction/doctor"]}, [
        (u"cmk/docker_object", u"container"),
        (u"cmk/docker_image", u"library:8080/fiction/doctor"),
        (u"cmk/docker_image_name", u"doctor"),
    ]),
])
def test_docker_container_host_labels(check_manager, parsed, label_value_pairs):
    check = check_manager.get_check('docker_container_status')
    _docker_container_host_labels = check.context['_docker_container_host_labels']
    assert list(_docker_container_host_labels(parsed)) == label_value_pairs
