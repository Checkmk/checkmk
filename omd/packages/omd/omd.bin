#!/omd/versions/###OMD_VERSION###/bin/python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This file is part of OMD - The Open Monitoring Distribution

isort:skip_file"""

import os
import sys

PY_MAJ = sys.version_info[0]
PY_MIN = sys.version_info[1]
PY_PAT = sys.version_info[2]

# This hack here is needed to prevent "omd update" problems when updating
# as site user (e.g. from 1.4 versions older than 1.4.0p17)
# Previous versions did not unset PYTHONPATH/LD_LIBRARY_PATH before execv()
# to the newer version "omd" command which made the newer OMD load the old
# python libraries. Newer versions unset these variables before, so this
# additional execv() is only needed when updating from older versions.
# Further, we saw issues with Python patch release, which introduce breaking changes on private APIs.
# This happened during our bump from Python 3.11.2 to 3.11.5, see https://github.com/python/cpython/issues/108525.
if (
    len(sys.argv) > 1
    and "update" in sys.argv
    and (
        (PY_MAJ == 2 and PY_MIN == 7 and PY_PAT < 14)
        or (PY_MAJ == 3 and PY_MIN == 11 and PY_PAT < 5)
        or (PY_MAJ == 3 and PY_MIN < 11)
    )
):
    # Prevent inheriting environment variables from this versions/site environment
    # into the execed omd call. The OMD call must import the python version related
    # modules and libaries. This only works when PYTHONPATH and LD_LIBRARY_PATH are
    # not already set when calling "omd update"
    try:
        del os.environ["PYTHONPATH"]
    except KeyError:
        pass

    try:
        del os.environ["LD_LIBRARY_PATH"]
    except KeyError:
        pass
    os.execv(sys.argv[0], sys.argv)
    sys.exit("Cannot run execv() %s" % sys.argv[0])

# Needs to be after the hacks above
import omdlib.main  # noqa: E402

if __name__ == "__main__":
    omdlib.main.main()
