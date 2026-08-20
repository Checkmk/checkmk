load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "fields",
    srcs = [
        "__init__.py",
        "base.py",
        "primitives.py",
        "validators.py",
    ],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//tests/unit:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:hostaddress",
        requirement("marshmallow"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":fields"],
)
