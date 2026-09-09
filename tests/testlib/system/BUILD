load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

# Helpers for tests that drive a running Checkmk site or containers:
# site setup, agent handling, REST and web sessions, docker images.
# Never imported by unit-level code; system tests run via pytest, so
# this target mainly feeds mypy and lint.
py_library(
    name = "system",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//non-free/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
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
        requirement("clickhouse-connect"),
        requirement("cryptography"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("fastapi"),
        requirement("flask"),
        requirement("pexpect"),
        requirement("playwright"),
        requirement("psutil"),
        requirement("pydantic"),
        requirement("pyjwt"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pytest-mock"),
        requirement("pyyaml"),
        requirement("requests"),
    ],
)
