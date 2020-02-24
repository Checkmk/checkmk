# coding=utf-8
import subprocess
import sys

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import


def test_no_callsite():
    path = Path(__file__, '../../../../checks').resolve()
    exit_code = subprocess.call(["grep", "-rl", "'memory.include'", str(path)])
    assert exit_code == 1  # nothing found
