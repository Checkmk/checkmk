#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
from copy import deepcopy
from os import environ, getenv

import schemathesis
from hypothesis import HealthCheck, Phase, settings, strategies, Verbosity

allow_redirects = False

# generic issues that affect testing as a whole and should always be suppressed
suppressed_issues = {
    "CMK-11886"  # no real fix possible, caused by webserver if SCHEMATHESIS_ALLOW_NULLS=1
}
if "SCHEMATHESIS_SUPPRESS" in environ:
    suppressed_issues.update(set(getenv("SCHEMATHESIS_SUPPRESS", "").upper().split(",")))
else:
    suppressed_issues.update(
        {
            "CMK-21677",
            "CMK-21783",
            "CMK-21807",
            "CMK-21809",
        }
    )
for issue in set(getenv("SCHEMATHESIS_ALLOW", "").upper().split(",")):
    suppressed_issues.discard(issue)

# default "string" strategy
default_string_pattern = "^[A-Za-z0-9_-]{1,15}$"
default_identifier_pattern = "^[A-Za-z][A-Za-z0-9_-]{0,15}$"
schemathesis.register_string_format(
    "string", strategies.from_regex(default_string_pattern, fullmatch=True)
)
schemathesis.register_string_format(
    "identifier", strategies.from_regex(default_identifier_pattern, fullmatch=True)
)

# hypothesis settings
current_profile = getenv("SCHEMATHESIS_PROFILE", getattr(settings, "_current_profile", "default"))

# default settings profile
default_settings = {
    "deadline": 5000,
    "derandomize": False,
    "max_examples": 1,
    "phases": [
        Phase.explicit,
        Phase.generate,
        Phase.explain,
    ],
    "stateful_step_count": 5,
    "suppress_health_check": [
        HealthCheck.filter_too_much,
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
    ],
    "verbosity": Verbosity.normal,
}
settings.register_profile("default", None, **default_settings)
settings.load_profile("default")

# qa settings profile
qa_settings = deepcopy(default_settings)
qa_settings.update({"verbosity": Verbosity.verbose})
settings.register_profile("qa", None, **qa_settings)

# ci settings profile
ci_settings = deepcopy(default_settings)
ci_settings.update({"derandomize": True, "max_examples": 10, "verbosity": Verbosity.quiet})
settings.register_profile("ci", None, **ci_settings)

# debug settings profile
debug_settings = deepcopy(default_settings)
debug_settings.update({"verbosity": Verbosity.debug})
settings.register_profile("debug", None, **debug_settings)

settings.load_profile(current_profile)
