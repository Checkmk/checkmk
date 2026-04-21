load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

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
        "//packages/cmk-livestatus-client:py_livestatus",
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
        "//cmk/gui:sites",
        "//cmk/gui:type_defs",
        "//cmk/gui/graphing",
        "//cmk/gui/userdb",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/gui/watolib:password_store",
        "//cmk/gui/watolib:tag_config_file",
        "//cmk/utils",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:user",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("cryptography"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("pyparsing"),
    ],
)
