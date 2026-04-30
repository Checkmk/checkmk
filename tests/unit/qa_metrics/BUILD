load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "qa_metrics",
    testonly = True,
    srcs = [
        "__init__.py",
        "_db_stubs.py",
    ],
    deps = [requirement("psycopg")],
)
