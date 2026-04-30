load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "db",
    srcs = [
        "__init__.py",
        "connection.py",
        "helpers.py",
        "table.py",
    ],
    imports = ["../../.."],
    deps = [
        requirement("psycopg"),
    ],
)
