load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

package(default_visibility = [":__subpackages__"])

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "utils",
    size = "small",
    timeout = "moderate",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    data = glob(
        include = ["**/test-files/**"],
        exclude = ["**/*.py"],
    ),
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        "//cmk/utils",
        "//cmk/utils:msi_patch",
        "//cmk/utils:redis",
        "//cmk/utils:werks",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-crypto",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:utils",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("fakeredis"),
        requirement("time-machine"),
        requirement("icalendar"),
        requirement("cryptography"),
        requirement("python-dateutil"),
        requirement("pytest"),
        requirement("pytest-asyncio"),
        requirement("recurring-ical-events"),
        requirement("werkzeug"),
        requirement("flask"),
        requirement("pytest-random-order"),
    ],
)
