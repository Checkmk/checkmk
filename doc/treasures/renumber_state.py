#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import pathlib
import shutil
import sys
from itertools import count

import cmc_proto.state_pb2

parser = argparse.ArgumentParser(
    prog="renumber_state", description="Renumbers comments and downtimes of a cmc state.pb file"
)
parser.add_argument("state_path", type=pathlib.Path)
downtime_id_arg = parser.add_argument("-d", "--downtime-start-id", type=int)
comment_id_arg = parser.add_argument("-c", "--comment-start-id", type=int)
parser.add_argument(
    "-b",
    "--backup-path",
    default="state.pb.bak",
    type=pathlib.Path,
    help="Either an absolute path to a backup file or a filename which will be created relative to the state file path.",
)

args = parser.parse_args()

if args.downtime_start_id is None and args.comment_start_id is None:
    sys.exit(0)

real_backup_path = (
    args.backup_path
    if args.backup_path.is_absolute()
    else args.state_path.parent / args.backup_path
)

state = cmc_proto.state_pb2.StateFile()
with open(args.state_path, "rb") as f:
    state.ParseFromString(f.read())

if args.downtime_start_id is not None:
    ids = count(args.downtime_start_id)
    for downtime, next_id in zip(state.downtimes.entries, ids):
        downtime.id = next_id
    state.downtimes.next_id = next(ids)
    print(
        f"Renumbered {len(state.downtimes.entries)} downtimes. Next ID is {state.downtimes.next_id}"
    )

if args.comment_start_id is not None:
    ids = count(args.comment_start_id)
    for comment, next_id in zip(state.comments.entries, ids):
        comment.id = next_id
    state.comments.next_id = next(ids)
    print(f"Renumbered {len(state.comments.entries)} comments. Next ID is {state.comments.next_id}")

if real_backup_path.exists():
    print(
        f"{real_backup_path} already exists. Please move or rename the file to prevent data loss."
    )
    sys.exit(1)

shutil.copy(args.state_path, real_backup_path)
print(f"Copied state file to {real_backup_path}")

with open(args.state_path, "wb") as o:
    o.write(state.SerializeToString())
    print(f"Wrote updated state file to {args.state_path}")
