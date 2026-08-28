load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "change_quality",
    testonly = True,
    srcs = [
        "__init__.py",
        "components.py",
        "detect_test.py",
        "detect_test_rust.py",
        "repo.py",
        "rows.py",
        "state.py",
        "walk.py",
    ],
    data = ["schema.sql"],
    imports = ["../../.."],
    deps = [
        "//tests/qa_metrics/db",
        requirement("cmk-werk-zeug"),
    ],
)

py_binary(
    name = "push",
    testonly = True,
    srcs = ["push.py"],
    imports = ["../../.."],
    deps = [
        ":change_quality",
        "//packages/cmk-werks:tool",
        "//tests/qa_metrics/db",
    ],
)

# check_gaps as a library so its logic (exit-code contract, gap computation) is
# unit-testable; the binary is a thin entry point over it.
py_library(
    name = "check_gaps_lib",
    testonly = True,
    srcs = ["check_gaps.py"],
    imports = ["../../.."],
    deps = [
        ":change_quality",
        "//packages/cmk-werks:tool",
        "//tests/qa_metrics/db",
        requirement("psycopg"),
    ],
)

py_binary(
    name = "check_gaps",
    testonly = True,
    srcs = ["check_gaps.py"],
    imports = ["../../.."],
    deps = [
        ":change_quality",
        "//packages/cmk-werks:tool",
        "//tests/qa_metrics/db",
        requirement("psycopg"),
    ],
)
