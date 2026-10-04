load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "helper",
    size = "small",
    srcs = glob(["**/*.py"]),
    args = ["--random-order-bucket=global"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/automations:helper",
        "//tests/testlib/common",
        "//tests/unit:conftest",
        requirement("fakeredis"),
        requirement("fastapi"),
        requirement("httpx"),
        requirement("pytest-asyncio"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
        requirement("requests"),
        requirement("starlette"),
        requirement("time-machine"),
        requirement("watchdog"),
    ],
)
