#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence


def migrate_mapped_states(model: object, state_names: Sequence[str]) -> Mapping[str, object]:
    """Turn the formerly listed (state name, service state) pairs into a mapping

    A state the list left out used to get the service state configured as
    "mapped_states_default" if there was one; it is now set explicitly.
    """
    if not isinstance(model, dict):
        raise TypeError(f"Expected a mapping of parameters, got {model!r}")
    if not isinstance(pairs := model.get("mapped_states"), list):
        return model
    mapped_states = dict(pairs)
    if "mapped_states_default" in model:
        mapped_states = dict.fromkeys(state_names, model["mapped_states_default"]) | mapped_states
    return {**model, "mapped_states": mapped_states}
