#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.werks.convert import werkv1_to_werkv2
from cmk.werks.format import format_as_werk_v1
from cmk.werks.parse import parse_werk_v2

WERK_V1_SIMPLE = """Title: Simple Title
Class: fix
Compatible: compat
Component: wato
Date: 1500000000
Edition: cre
Level: 1
Version: 2.2.0p1

Short description

H2: headline

LI: one
LI: two

C+:
code
C-:

smth
"""

WERK_V1 = """Title: Fix rule analyzation issues on service object parameter page
Class: fix
Compatible: compat
Component: wato
Date: 1576509403
Edition: cre
Knowledge: undoc
Level: 1
State: unknown
Version: 2.0.0i1

Two issues on the object parameter page have been fixed:

The links to the rules that are used to create "Classical active and passive
Monitoring checks" services on the WATO "Parameters of service" page could
be wrong in case there were disabled rules on top of the rule list.

The effective settings of rulesets could be displayed with a wrong value.

F+:
{
   ...
}
F-:

F+:filename
content
F-:


C+:
code
C-:


LI: check_mk_agent.aix
LI: check_mk_agent.freebsd
LI: check_mk_agent.macosx

"""

WERK_V1_RESULT = """[//]: # (werk v2)
# Fix rule analyzation issues on service object parameter page

key | value
--- | ---
compatible | yes
version | 2.0.0i1
date | 2019-12-16T15:16:43+00:00
level | 1
class | fix
component | wato
edition | cre

Two issues on the object parameter page have been fixed:

The links to the rules that are used to create "Classical active and passive
Monitoring checks" services on the WATO "Parameters of service" page could
be wrong in case there were disabled rules on top of the rule list.

The effective settings of rulesets could be displayed with a wrong value.

```
{
   ...
}
```

`filename`
```
content
```


```
code
```


* check_mk_agent.aix
* check_mk_agent.freebsd
* check_mk_agent.macosx"""


def test_convert_werk_simple() -> None:
    text, werk_id = werkv1_to_werkv2(WERK_V1, 1234)
    assert werk_id == 1234
    assert text == WERK_V1_RESULT


def test_roundtrip() -> None:
    werk2, werk_id = werkv1_to_werkv2(WERK_V1_SIMPLE, 1234)
    assert werk_id == 1234
    werk1 = format_as_werk_v1(parse_werk_v2(werk2, "1234"))
    assert werk1 == WERK_V1_SIMPLE
