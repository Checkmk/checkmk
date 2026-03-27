load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "legacy_checks",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/editions:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/legacy_includes",
        "//cmk/plugins",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugins:graylog",
        "//packages/cmk-plugins:lib",
        requirement("pydantic"),
        requirement("python-dateutil"),
    ],
)
