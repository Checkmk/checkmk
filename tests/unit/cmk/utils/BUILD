load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

py_test(
    name = "utils",
    size = "small",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"] + glob(
        include = ["**/test-files/**"],
        exclude = ["**/*.py"],
    ),
    env = {"EDITION": "community"},
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        "//cmk/utils",
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
