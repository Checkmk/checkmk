load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

# Helpers for tests that drive a running Checkmk site or containers:
# site setup, agent handling, REST and web sessions, docker images.
# Never imported by unit-level code; system tests run via pytest, so
# this target mainly feeds mypy and lint.
py_library(
    name = "system",
    testonly = True,
    srcs = glob(
        ["**/*.py"],
        exclude = ["shard_planning.py"],  # dedicated target :shard_planning, must stay pytest free
    ),
    imports = ["../../.."],
    visibility = [
        "//non-free/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":shard_planning",
        "//cmk/base",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/graphing",
        "//cmk/gui/openapi/spec/editions",
        "//cmk/gui/watolib",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-relay-protocols",
        "//tests/testlib/common",
        requirement("beautifulsoup4"),
        requirement("checkmk-dev-tools"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("faker"),
        requirement("psutil"),
        requirement("pydantic"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("requests"),
    ],
)

# The shard planning, split off so it stays importable without pytest:
# tests/scripts/resolve_shard_durations.py runs it in the "Resolve shard
# durations" CI stage, in a container with no pytest installed. Declaring no
# pytest dep here turns a future `import pytest` into a mypy failure.
py_library(
    name = "shard_planning",
    testonly = True,
    srcs = ["shard_planning.py"],
    imports = ["../../.."],
    visibility = [
        "//non-free/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//tests:pkg_marker",
        requirement("checkmk-dev-tools"),
        requirement("requests"),
    ],
)
