load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

package(default_visibility = [":__subpackages__"])

py_cmk_test(
    name = "utils",
    size = "small",
    timeout = "moderate",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    data = glob(
        include = ["**/test-files/**"],
        exclude = ["**/*.py"],
    ),
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/gui:request_globals",
        "//cmk/utils",
        "//cmk/utils:msi_patch",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-crypto",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-werks:site",
        "//packages/cmk-wsgi",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("fakeredis"),
        requirement("time-machine"),
        requirement("icalendar"),
        requirement("cryptography"),
        requirement("python-dateutil"),
        requirement("pytest-asyncio"),
        requirement("recurring-ical-events"),
        requirement("werkzeug"),
        requirement("flask"),
        requirement("pytest-random-order"),
    ],
)
