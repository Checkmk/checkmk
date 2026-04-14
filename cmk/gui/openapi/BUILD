load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([".f12"])

py_library(
    name = "utils",
    srcs = ["utils.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/utils",
        requirement("docstring-parser"),
        requirement("werkzeug"),
    ],
)

py_library(
    name = "permission_tracking",
    srcs = ["permission_tracking.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:ctx_stack",
    ],
)

py_library(
    name = "_type_adapter",
    srcs = ["_type_adapter.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("pydantic"),
    ],
)

py_library(
    name = "openapi_init",
    srcs = [
        "__init__.py",
        "version.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects",
    ],
)

# Temporary: openapi files that still belong to the monolithic //cmk/gui target.
filegroup(
    name = "gui_srcs",
    srcs = ["registration.py"],
    visibility = ["//cmk/gui:__pkg__"],
)
