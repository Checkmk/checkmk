load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "base",
    srcs = [
        "base.py",
        "mixins.py",
        "utils.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/fields",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
        requirement("apispec"),
        requirement("marshmallow"),
    ],
)

py_library(
    name = "fields",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "base.py",
            "mixins.py",
            "utils.py",
        ],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":base",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/userdb",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:groups_io",
        "//cmk/gui/watolib:password_store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-livestatus-client",
        requirement("cryptography"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("pyparsing"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":base",
        ":fields",
    ],
)
