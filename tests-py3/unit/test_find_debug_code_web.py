# encoding: utf-8

from pathlib import Path
from testlib import cmk_path


def test_find_debug_code():
    to_scan = _files_to_scan()
    assert len(to_scan) > 20

    for path in to_scan:
        with path.open(encoding="utf-8") as f:
            for line in f:
                l = line.lstrip()
                assert not l.startswith("html.debug("), "Found \"html.debug(...)\" call"


def _files_to_scan():
    to_scan = [Path(cmk_path(), "web", "app", "index.wsgi")]
    for matched_file in Path(cmk_path(), "cmk", "gui").glob("**/*.py"):
        if matched_file.is_file():
            to_scan.append(matched_file)
    return to_scan
