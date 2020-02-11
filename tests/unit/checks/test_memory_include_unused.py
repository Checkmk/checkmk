# coding=utf-8
import subprocess
from pathlib2 import Path


def test_no_callsite():
    path = Path(__file__, '../../../../checks').resolve()
    exit_code = subprocess.call(["grep", "-rl", "'memory.include'", str(path)])
    assert exit_code == 1  # nothing found
