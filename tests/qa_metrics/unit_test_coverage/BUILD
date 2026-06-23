load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "unit_test_coverage",
    srcs = [
        "__init__.py",
        "add_missing_coverage.py",
        "code_coverage_summary.py",
    ],
    imports = ["../../.."],
)

py_binary(
    name = "store_code_coverage",
    srcs = ["store_code_coverage.py"],
    data = ["code_coverage_tables.sql"],
    imports = ["../../.."],
    deps = [
        requirement("psycopg"),
        "//tests/qa_metrics/db",
    ],
)

sh_library(
    name = "code_coverage_sh",
    srcs = ["code_coverage.sh"],
)
