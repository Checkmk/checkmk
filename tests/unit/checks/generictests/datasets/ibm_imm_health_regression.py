#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_imm_health"


info = [["223523"], ["2342"], ["234"], ["23352"]]


discovery = {"": [(None, None)]}


checks = {"": [(None, {}, [(3, "23352(234)", [])])]}
