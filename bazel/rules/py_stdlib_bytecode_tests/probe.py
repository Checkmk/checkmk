#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Prints where Python looks for the bytecode of email.feedparser, of the standard library."""

# Not imported at interpreter startup, so this import decides where its code comes from.
import email.feedparser
import sys

sys.stdout.write(f"{email.feedparser.__spec__.cached}\n")
