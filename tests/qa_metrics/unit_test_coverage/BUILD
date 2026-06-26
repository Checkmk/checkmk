load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "unit_test_coverage",
    srcs = [
        "__init__.py",
        "rows.py",
        "summary.py",
    ],
    data = ["schema.sql"],
    imports = ["../../.."],
    deps = [
        "//tests/qa_metrics/db",
    ],
)

py_binary(
    name = "upload",
    srcs = ["upload.py"],
    imports = ["../../.."],
    deps = [
        ":unit_test_coverage",
        requirement("psycopg"),
        "//tests/qa_metrics/db",
    ],
)

py_binary(
    name = "add_missing",
    srcs = ["add_missing.py"],
)

py_binary(
    name = "summary",
    srcs = ["summary.py"],
)

sh_library(
    name = "main_sh",
    srcs = ["main.sh"],
)
