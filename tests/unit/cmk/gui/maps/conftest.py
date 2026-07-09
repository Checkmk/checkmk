#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared fixtures for the Maps GUI tests.

The "all objects" NagVis fixture lives here because two suites need it: the
importer tests (``test_cfg_import``) and the map-shape contract test, which feeds
the same parsed map through the REST bridge. It is inlined rather than a sidecar
.cfg file, since the test target's runfiles only carry Python sources.
"""

import pytest

from cmk.maps.gui._cfg_import import cfg_to_map
from cmk.maps.shared.map_payload import MapPayload

_ALL_OBJECTS_CFG = """\
define global {
alias=All Objects
backend_id=ZWEIFUENF
iconset=std_big
object_id=00000a
}

define host {
host_name=localhost
x=200
y=120
object_id=h00001
only_hard_states=1
recognize_services=1
}

define service {
host_name=localhost
service_description=Memory
x=420
y=120
object_id=s00001
view_type=icon
only_hard_states=1
}

define service {
host_name=localhost
service_description=CPU load
x=620
y=120
object_id=s00002
view_type=gadget
gadget_url=std_speedometer.php
}

define service {
host_name=localhost
service_description=Interface 2
x=200,800
y=320,320
object_id=s00003
view_type=line
}

define hostgroup {
hostgroup_name=linux-servers
x=200
y=480
object_id=hg0001
}

define servicegroup {
servicegroup_name=disk-services
x=420
y=480
object_id=sg0001
}

define line {
x=620,820
y=480,560
line_type=10
object_id=l00001
}

define line {
x=820,1020
y=480,560
line_type=11
object_id=l00002
}

define line {
x=620,820
y=560,640
line_type=12
object_id=l00003
}

define service {
host_name=localhost
service_description=Interface 2
line_label_in=in
line_label_out=out
line_width=5
x=200,1020
y=720,720
line_type=15
view_type=line
object_id=l00004
}

define textbox {
text=Hello&nbsp;<b>World</b><br>second line
x=200
y=820
w=300
h=60
object_id=tb0001
}

define shape {
icon=std_nagvis.png
x=560
y=820
object_id=sh0001
}

define map {
map_name=other-map
x=820
y=820
object_id=m00001
}

define aggr {
name=Host localhost
backend_id=ZWEIFUENF_bi
x=1020
y=120
object_id=ag0001
}

define service {
host_name=localhost
service_description=Filesystem /
x=1020
y=320
object_id=s00004
url=https://example.com/dashboard
url_target=main
}
"""


@pytest.fixture
def all_objects_map() -> MapPayload:
    return cfg_to_map(_ALL_OBJECTS_CFG, "all-objects")
