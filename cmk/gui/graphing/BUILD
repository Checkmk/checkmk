load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "graphing",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["openapi/**"],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/form_specs",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//cmk/gui/valuespec",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-graphing-engine",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//packages/cmk-web/cmk/web/utils",
        requirement("python-dateutil"),
        requirement("tzlocal"),
        requirement("matplotlib"),
    ],
)

py_library(
    name = "openapi",
    srcs = glob(["openapi/**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":graphing",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/visuals",
        "//packages/cmk-graphing-engine",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-web/cmk/web/utils",
    ],
)
