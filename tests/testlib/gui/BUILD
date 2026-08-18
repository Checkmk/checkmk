load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "gui",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    tags = [
        "deballast-keep=//tests/testlib/common:empty_config",  # GUI-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//tests/testlib/common:repo",  # GUI-test fixture bundle, loaded at runtime / provided to consumers
        "deballast-keep=//tests/testlib/common:utils",  # GUI-test fixture bundle, loaded at runtime / provided to consumers
    ],
    visibility = [
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//tests:__pkg__",
        "//tests/openapi:__subpackages__",
        "//tests/testlib/unit:__pkg__",
        "//tests/unit:__subpackages__",
    ],
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/plugins/wato/check_parameters:stub",
        "//cmk/gui/userdb",
        "//cmk/gui/watolib:password_store",
        "//packages/cmk-wsgi",
        "//tests/testlib:rest_api_client",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("flask"),
        requirement("pytest-mock"),
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)
