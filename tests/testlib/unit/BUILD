load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "unit",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    tags = [
        "deballast-keep=//cmk/gui:app",  # unit-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//cmk/gui/graphing:graphing",  # unit-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//cmk/gui/openapi/endpoints:endpoints",  # unit-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//cmk/gui/openapi/framework:framework",  # unit-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//cmk/gui/openapi/restful_objects:type_defs",  # unit-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//cmk/gui/rest_api_types:notifications",  # unit-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//cmk/gui/userdb:userdb",  # unit-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//packages/cmk-crash:crash",  # unit-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//tests/testlib/gui:gui",  # unit-test fixture bundle, loaded at runtime / provided to consumers
    ],
    visibility = [
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/base/config",
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/graphing",
        "//cmk/gui/mkeventd",
        "//cmk/gui/nodevis:utils",
        "//cmk/gui/openapi/endpoints",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/rest_api_types:notifications",
        "//cmk/gui/userdb",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:password_store",
        "//packages/cmk-crash:crash",
        "//tests/testlib:rest_api_client",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        "//tests/testlib/gui",
        requirement("flask"),
        requirement("pytest-mock"),
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)
