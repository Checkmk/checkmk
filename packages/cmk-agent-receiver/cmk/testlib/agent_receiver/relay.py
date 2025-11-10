#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid

from cmk.agent_receiver.relay.lib.shared_types import RelayID


def random_relay_id() -> RelayID:
    """Generates a random RelayID for testing purposes."""
    return RelayID(str(uuid.uuid4()))
