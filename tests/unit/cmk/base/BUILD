load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

filegroup(
    name = "bakery_test_files",
    srcs = glob(["plugins/bakery/test_*.py"]),
    visibility = ["//tests/unit/cmk/base/nonfree/pro:__pkg__"],
)

py_cmk_test(
    name = "base",
    size = "small",
    timeout = "moderate",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/plugins",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:utils",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("fakeredis"),
        requirement("fastapi"),
        requirement("httpx"),
        requirement("starlette"),
        requirement("time-machine"),
        requirement("requests"),
        requirement("watchdog"),
    ],
)
