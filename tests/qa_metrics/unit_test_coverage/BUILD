load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "unit_test_coverage",
    srcs = [
        "__init__.py",
        "add_missing_coverage.py",
        "code_coverage_summary.py",
        "rows.py",
    ],
    data = ["schema.sql"],
    imports = ["../../.."],
    deps = [
        "//tests/qa_metrics/db",
    ],
)

py_binary(
    name = "store_code_coverage",
    srcs = ["store_code_coverage.py"],
    imports = ["../../.."],
    deps = [
        ":unit_test_coverage",
        requirement("psycopg"),
        "//tests/qa_metrics/db",
    ],
)

sh_library(
    name = "code_coverage_sh",
    srcs = ["code_coverage.sh"],
)
