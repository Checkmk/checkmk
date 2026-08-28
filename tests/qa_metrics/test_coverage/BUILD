load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "file_lists",
    testonly = True,
    srcs = ["_file_lists.py"],
    imports = ["../../.."],
)

py_library(
    name = "test_coverage",
    testonly = True,
    srcs = [
        "__init__.py",
        "owned_files.py",
        "rows.py",
        "summary.py",
    ],
    data = ["schema.sql"],
    imports = ["../../.."],
    deps = [
        ":file_lists",
        "//tests/qa_metrics/components",
        "//tests/qa_metrics/db",
    ],
)

py_binary(
    name = "upload",
    testonly = True,
    srcs = ["upload.py"],
    imports = ["../../.."],
    deps = [
        ":test_coverage",
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
    testonly = True,
    srcs = ["summary.py"],
)

py_binary(
    name = "owned_files",
    testonly = True,
    srcs = ["owned_files.py"],
    imports = ["../../.."],
    deps = [
        ":file_lists",
        "//tests/qa_metrics/components",
    ],
)

sh_library(
    name = "main_sh",
    srcs = ["main.sh"],
)
