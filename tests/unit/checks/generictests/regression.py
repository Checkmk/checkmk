"""Script to create regression tests

This is actually a script, but we need all the test magic,
so call it as a test.

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

This will create a file called '~/tmp/example_regression.py'.

3) In order to use it as a test case move it to the folder
[check_mk]/tests/unit/checks/generictests/datasets/.
Make sure the file is a valid python module:

 mv /tmp/example_regression.py \
 ~/git/check_mk/tests/unit/checks/generictests/datasets/nfsmounts_1.py

"""
import os
import sys
import pprint
import time
from importlib import import_module

import generictests.run


class WritableDataset(object):
    def __init__(self, filename, init_dict):
        self.comments = ['-*- encoding: utf-8', 'yapf: disable']
        self.filename = filename
        self.writelist = (
            'checkname',
            'freeze_time',
            'info',
            'parsed',
            'discovery',
            'checks',
            'extra_sections',
            'mock_host_conf',
            'mock_host_conf_merged',
            'mock_item_state',
        )
        self.checkname = init_dict.get('checkname', None)
        self.info = init_dict.get('info', None)
        freeze_time = init_dict.get('freeze_time', None)
        if freeze_time == "":
            freeze_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.freeze_time = freeze_time
        self.parsed = init_dict.get('parsed', None)
        self.discovery = init_dict.get('discovery', {})
        self.checks = {}
        self.extra_sections = init_dict.get('extra_sections', {})
        self.mock_host_conf = init_dict.get('mock_host_conf', {})
        self.mock_host_conf_merged = init_dict.get('mock_host_conf_merged', {})
        self.mock_item_state = init_dict.get('mock_item_state', {})

    def write(self, directory):
        content = []
        for k in self.writelist:
            v = getattr(self, k)
            if not v:
                continue
            k_str = '%s = ' % k
            v_str = pprint.pformat(v).replace('\n', '\n' + ' ' * len(k_str))
            content += ['', '', k_str + v_str]

        if not content:
            return

        with open('%s/%s' % (directory, self.filename.split("/")[-1]), 'w') as f:
            for comment in self.comments:
                f.write('# %s\n' % comment)
            f.write('\n'.join(content))


def test_main(check_manager, datasetfile):
    """Script to create test datasets.

    This is a script. But we need the py.test environment, so it comes in the
    shape of a test. Provide the above arguments using
    "--argument_name argument_value"
    """
    if not datasetfile:
        raise ValueError("must provide '--datasetfile'")

    dirn, modn = os.path.split(datasetfile)
    sys.path.insert(0, dirn)
    input_data = import_module(os.path.splitext(modn)[0])
    sys.path.pop(0)

    regression = WritableDataset(datasetfile.replace('.py', '_regression.py'), vars(input_data))

    generictests.run(check_manager, regression, write=True)

    directory = os.path.join(os.path.dirname(__file__), "datasets")
    regression.write(directory)
    return
