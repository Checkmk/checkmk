"""Helpers for generictests"""
from pathlib2 import Path

EXCLUDES = ('', '__init__', 'conftest', '__pycache__')

DATASET_DIR = Path(__file__).absolute().parent / 'datasets'

DATASET_FILES = {f for f in DATASET_DIR.glob("*.py") if f.stem not in EXCLUDES}

DATASET_NAMES = {f.stem for f in DATASET_FILES}
