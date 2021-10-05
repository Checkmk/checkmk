#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Script to create regression tests

This is actually a script, but we need all the test magic,
so call it as a test.

You can use this script to do one of the following two things:
    A. Create a new test from scratch
    B. Update all or one selected test to match the current status quo


A. Create a new test from scratch

    In order to create a regression test for a check, do the following:

    1) Create a minimal compliant dataset as described in generictests/__init__.py.
       For example, let's create the file ~/tmp/example.py with the content

          checkname = 'nfsmounts'

          info = [
              ['/path/to/share', 'ok', '1611668', '794767', '712899', '32768']
          ]

       The checkname variable should not include the subcheck name.
       The info variable should be defined exactly as expected by the parse or
       discovery function, including node info or extra sections, if necessary.

    2) From this file we create a regression test dataset by running

       py.test -T unit tests/unit/checks/generictests/regression.py \
       --datasetfile ~/tmp/example.py

      This will create a file called '../datasets/example.py' (relative to the
      path of this script, i.e. __file__), if that file already exists,
      it is postfixed by '_regression.py'.
      If you specify '--inplace' in the command line, the existing file
      '--datasetfile' will be overwritten.

    3) (only if you used "--inplace"): In order to use the resulting file as a
       test case, move it to the folder ../datasets/ (again: relative to the
        path of this script, i.e. __file__).

    Make sure the file is a valid python module. Since the files content
    is yapf'ed, I suggest you do not change the formatting (which simplifies
    case B, if and when you need it).

B. Update all or one selected test to match the current status quo

    If you made changes that affect more than one test file, you can
    overwrite all existing test datasets. To do so, run

    py.test -T unit tests/unit/checks/generictests/regression.py --inplace

    This will take quite some time, and overwrite ALL test datasets.
    You can restrict this process to a subset of files using
     * the paramter "--datasetfile path/to/file"
     * the regular "-k test-name-pattern"  option to py.test

"""
import ast
import os
import sys
import time
from importlib import import_module
from pathlib import Path
from typing import Any, Iterable

import yapf  # type: ignore[import]

from .run import run

YAPF_STYLE = {
    "dedent_closing_brackets": 1,
    "split_before_closing_bracket": 1,
}


class WritableDataset:
    def __init__(self, init_dict):
        self.writelist = (
            "checkname",
            "freeze_time",
            "info",
            "parsed",
            "discovery",
            "checks",
            "extra_sections",
            "mock_host_conf",
            "mock_host_conf_merged",
            "mock_item_state",
        )
        self.checkname = init_dict.get("checkname", None)
        self.info = init_dict.get("info", None)
        freeze_time = init_dict.get("freeze_time", None)
        if freeze_time == "":
            freeze_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.freeze_time = freeze_time
        self.parsed = init_dict.get("parsed", None)
        self.discovery = init_dict.get("discovery", {})
        self.checks = init_dict.get("checks", {})
        self.extra_sections = init_dict.get("extra_sections", {})
        self.mock_host_conf = init_dict.get("mock_host_conf", {})
        self.mock_host_conf_merged = init_dict.get("mock_host_conf_merged", {})
        self.mock_item_state = init_dict.get("mock_item_state", {})

    def update_check_result(self, subcheck, new_entry):
        subcheck_data = self.checks.setdefault(subcheck, [])[:]
        for idx, present_result in enumerate(subcheck_data):
            if present_result[:2] == new_entry[:2]:
                self.checks[subcheck][idx] = new_entry
                return
        self.checks[subcheck].append(new_entry)

    def write(self, filename):
        content = []
        imports = set()
        for attr in self.writelist:
            value = getattr(self, attr)
            if not value:
                continue
            content.append("%s = %r" % (attr, value))
            imports |= self.get_imports(value)

        if not content:
            return

        content = list(sorted(imports)) + content

        yapfed_content, __ = yapf.yapflib.yapf_api.FormatCode(
            "\n\n".join(content),
            style_config=YAPF_STYLE,
        )

        with Path(filename).open("w") as handle:
            # Disabling yapf: yapf parses comment blocks and disables the next
            # lines if and only if the FIRST line of that block contains
            #   '# yapf: disable'
            # Does not work:
            #   '# -*- encoding: utf-8'
            #   '# yapf: disable'
            # Works:
            #   '# -*- encoding: utf-8'
            #   ''
            #   '# yapf: disable'
            comments = [
                "#!/usr/bin/env python3\n",
                "# -*- encoding: utf-8 -*-\n",
                "# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2\n",
                "# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and\n",
                "# conditions defined in the file COPYING, which is part of this source code package.\n",
                "\n",
                "# yapf: disable\n",
                "# type: ignore\n",
            ]
            handle.writelines(comments)
            handle.write(yapfed_content)

    def get_imports(self, value):
        try:
            ast.literal_eval(repr(value))
            return set()
        except ValueError:
            pass

        if isinstance(value, dict):
            iterate: Iterable[Any] = value.items()
        elif isinstance(value, (tuple, list)):
            iterate = value
        else:
            return {"from %s import %s" % (value.__module__, value.__class__.__name__)}

        imports = set()
        for val in iterate:
            imports |= self.get_imports(val)
        return imports


def _get_out_filename(datasetfile, inplace):
    if inplace:
        return datasetfile

    basename = os.path.basename(datasetfile)
    dirname = os.path.dirname(os.path.abspath(__file__))
    out_name = os.path.join(dirname, "datasets", basename)
    if not os.path.exists(out_name):
        return out_name

    return out_name.replace(".py", "_regression.py")


def test_main(fix_plugin_legacy, datasetfile, inplace):
    """Script to create test datasets.

    This is a script. But we need the py.test environment, so it comes in the
    shape of a test. Provide the datasetfile using
    "--datasetfile argument_value"
    (defaults to all found files)
    and (optional flag)
    "--inplace"
    """
    if not datasetfile:
        raise ValueError("must provide '--datasetfile'")

    dirn, modn = os.path.split(datasetfile)
    sys.path.insert(0, dirn)
    input_data = import_module(os.path.splitext(modn)[0])
    sys.path.pop(0)

    regression = WritableDataset(vars(input_data))

    run(fix_plugin_legacy.check_info, regression, write=True)

    regression.write(_get_out_filename(datasetfile, inplace))
