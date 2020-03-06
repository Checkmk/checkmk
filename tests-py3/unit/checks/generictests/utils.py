"""Helpers for generictests"""

import sys

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import

EXCLUDES = ('', '__init__', 'conftest', '__pycache__')

DATASET_DIR = Path(__file__).absolute().parent / 'datasets'

DATASET_FILES = {f for f in DATASET_DIR.glob("*.py") if f.stem not in EXCLUDES}

DATASET_NAMES = {f.stem for f in DATASET_FILES}
