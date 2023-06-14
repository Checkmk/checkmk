#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import sys

from apispec.yaml_utils import dict_to_yaml

from cmk.gui import main_modules
from cmk.gui.openapi import generate_data
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import application_and_request_context


def generate(args=None):
    if args is None:
        args = [None]

    with application_and_request_context():
        data = generate_data(target="debug")

    if args[-1] == "--json":
        output = json.dumps(data, indent=2).rstrip()
    else:
        output = dict_to_yaml(data).rstrip()

    return output


if __name__ == "__main__":
    # FIXME: how to load plugins? Spec is empty.
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occurred during plugin loading: {errors}")
    print(generate(sys.argv))
