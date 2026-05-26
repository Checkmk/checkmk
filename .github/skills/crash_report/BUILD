load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary", "py_library")

py_library(
    name = "crash_report_lib",
    srcs = [
        "__init__.py",
        "anonymize.py",
        "authenticate.py",
        "fetch_crash_data.py",
    ],
    visibility = [
        "//.claude/skills/crash_owner_rollup:__pkg__",
        "//.github/skills/crash_owner_rollup:__pkg__",
    ],
)

py_binary(
    name = "fetch_crash_data",
    srcs = [
        "__main__.py",
    ],
    main = "__main__.py",
    deps = [":crash_report_lib"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "unit_tests",
    srcs = [
        "__test__.py",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/test_anonymize.py",
        "tests/test_authenticate.py",
        "tests/test_fetch_crash_data.py",
    ],
    args = [
        "--import-mode=importlib",
        ".github/skills/crash_report/tests/",
    ],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":crash_report_lib",
        requirement("pytest"),
    ],
)
