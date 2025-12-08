#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from datetime import datetime

from cmk.livestatus_client import AddHostComment, LivestatusClient, SingleSiteConnection

try:
    omd_root = os.environ["OMD_ROOT"]
except KeyError:
    sys.stderr.write("This example is indented to run in an OMD site\n")
    sys.stderr.write("Please change socket_path in this example, if you are\n")
    sys.stderr.write("not using OMD.\n")
    sys.exit(1)

socket_path = "unix:" + omd_root + "/tmp/run/live"


def main() -> None:
    """Main function."""
    try:
        # Make a single connection for each query
        conn = SingleSiteConnection(socket_path)
        client = LivestatusClient(conn)

        # Add a host comment
        comment_command = AddHostComment(
            host_name="localhost",
            comment=f"This is a test comment added at {datetime.now()}",
            persistent=False,
            user="cmdbuild",
        )
        client.command(comment_command)
        print("Successfully added host comment.")

    except Exception as e:
        print(f"Livestatus error: {e}")


if __name__ == "__main__":
    main()
