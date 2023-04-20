#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from copy import deepcopy
from os import environ, getenv

import schemathesis
from hypothesis import HealthCheck, Phase, settings, strategies, Verbosity

known_issues = {
    "CMK-11886",
    "CMK-11900",
    "CMK-11924",
    "CMK-12044",
    "CMK-12048",
    "CMK-12116",
    "CMK-12125",
    "CMK-12140",
    "CMK-12143",
    "CMK-12144",
    "CMK-12181",
    "CMK-12182",
    "CMK-12217",
    "CMK-12220",
    "CMK-12235",
    "CMK-12241",
    "CMK-12246",
    "CMK-12261",
    "CMK-12320",
    "CMK-12321",
    "CMK-12326",
    "CMK-12327",
    "CMK-12334",
    "CMK-12335",
    "CMK-12380",
    "CMK-12421",
    "CMK-12543",
    "CMK-12544",
    "CMK-TODO",
    "CMK-RULE",
    "UNDEFINED-HTTP500",
    "INVALID-JSON",
}

if "TEST_OPENAPI_SUPPRESS" in environ:
    suppressed_issues = set(getenv("TEST_OPENAPI_SUPPRESS", "").upper().split(","))
else:
    suppressed_issues = known_issues
for issue in set(getenv("TEST_OPENAPI_ALLOW", "").upper().split(",")):
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
current_profile = settings._current_profile if hasattr(settings, "_current_profile") else "default"

# default settings profile
default_settings = {
    "deadline": 5000,
    "derandomize": False,
    "max_examples": 100,
    "phases": [Phase.explicit, Phase.generate],
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
ci_settings.update({"derandomize": True, "verbosity": Verbosity.quiet})
settings.register_profile("ci", None, **ci_settings)

# debug settings profile
debug_settings = deepcopy(default_settings)
debug_settings.update({"verbosity": Verbosity.debug})
settings.register_profile("debug", None, **debug_settings)

settings.load_profile(current_profile)
