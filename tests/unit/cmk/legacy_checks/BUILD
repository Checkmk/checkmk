load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

package(default_visibility = [":__subpackages__"])

py_cmk_test(
    name = "legacy_checks",
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
        "//cmk/legacy_checks",
        "//cmk/legacy_includes",
        "//tests/unit:conftest",
        requirement("marshmallow"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("time-machine"),
    ],
)
