load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/gui:auth",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/utils:middle",
        "//cmk/gui/watolib",
        "//tests/testlib/unit",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_cmk_test(
    name = "update_config",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["**/conftest.py"],
    ),
    args = [
        "--random-order-bucket=global",
    ],
    env = {"EDITION": "community"},
    tags = [
        "deballast-keep=//packages/cmk-maps:registration",  # FIXME: test exercises feature specific code
    ],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":conftest",
        "//cmk/update_config",
        "//packages/cmk-backup:utils",
        "//packages/cmk-ccc:store",
        "//packages/cmk-maps:registration",
        "//packages/cmk-plugin-apis:update_config",
        "//packages/cmk-plugins/cmk/plugins/lib",
        "//packages/cmk-werks:core",
        "//packages/cmk-werks:flavor_cmk",
        "//packages/cmk-werks:site",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:helpers",
        requirement("flask"),
        requirement("pytest-asyncio"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
    ],
)
