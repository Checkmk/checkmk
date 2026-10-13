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
        "scope.py",
        "source_files.py",
        "summary.py",
    ],
    data = ["schema.sql"],
    imports = ["../../.."],
    deps = [
        ":file_lists",
        requirement("coverage"),
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
    name = "scope",
    testonly = True,
    srcs = ["scope.py"],
    imports = ["../../.."],
    deps = [
        ":file_lists",
        requirement("coverage"),
    ],
)

py_binary(
    name = "source_files",
    testonly = True,
    srcs = ["source_files.py"],
    imports = ["../../.."],
    deps = [":file_lists"],
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
    name = "coverage_scripts",
    srcs = [
        "common.sh",
        "component.sh",
        "repository.sh",
    ],
)
