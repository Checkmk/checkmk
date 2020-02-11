"""Run all possible tests on every dataset found in generictests/datasets/

For simple check tests there is a framework which allows the creation of tests
via the definition of datasets.

These can be found in the subfolder ''checks/generictests/datasets'' of the
unittest folder.

In the most basic case, they define the ''checkname'' and ''info'' variable.
This will trigger a test run of the corresponding check using ''info'' as
argument to the parse or discovery function (see for example ''uptime_1.py'').
Without any further data, the test will be OK if the check does not crash.

If you also want to test for specific results you can either provide the
required variables manually (as in ''veritas_vcs_*.py''), or create a
regression test dataset as described in ''checks/generictests/regression.py''
"""
from importlib import import_module
import pytest  # type: ignore[import]
import testlib
import generictests

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("datasetname", generictests.DATASET_NAMES)
def test_dataset(check_manager, datasetname):
    with testlib.on_time(1572247138, "CET"):
        dataset = import_module("generictests.datasets.%s" % datasetname)
        generictests.run(check_manager, dataset)
