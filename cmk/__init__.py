#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
#    This file (cmk.__init__.py) is only kept to make
#    our dev tools (pylint & co) happy.
#    It will not be deployed, as cmk is supposed to be a
#    namespace that can be shadowed/extended using the local/
#    hierarchy.
#
#    This file must not contain any code.
#

# This is a quick fix for an import error encounterd when importing enterprise stuff
# during testing. Review this! CMK-4511
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)  # type: ignore[has-type] # don't worry about __path__
