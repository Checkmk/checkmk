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
from pathlib2 import Path
import pytest  # type: ignore
from testlib import cmk_path
import generictests

pytestmark = pytest.mark.checks

EXCLUDES = ('', '__init__', 'conftest', '__pycache__')

DATASET_DIR = Path(cmk_path(), 'tests', 'unit', 'checks', 'generictests', 'datasets')

DATASET_NAMES = {_f.stem for _f in DATASET_DIR.glob("*.py") if _f.stem not in EXCLUDES}


@pytest.mark.parametrize("datasetname", DATASET_NAMES)
def test_dataset(check_manager, datasetname):
    dataset = import_module("generictests.datasets.%s" % datasetname)
    generictests.run(check_manager, dataset)
