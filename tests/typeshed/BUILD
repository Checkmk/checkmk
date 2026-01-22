load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "marshmallow-oneofschema-stubs",
    srcs = [
        "marshmallow_oneofschema/__init__.pyi",
        "marshmallow_oneofschema/one_of_schema.pyi",
    ],
    visibility = ["//visibility:public"],
    deps = [requirement("marshmallow")],
)

py_library(
    name = "pyprof2calltree-stubs",
    srcs = [
        "pyprof2calltree.pyi",
    ],
    visibility = ["//visibility:public"],
)
