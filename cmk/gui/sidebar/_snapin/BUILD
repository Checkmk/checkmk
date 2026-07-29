load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "snapin_registry",
    srcs = [
        "_base.py",
        "_permission_section.py",
        "_registry.py",
    ],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/pagetypes",
        "//cmk/gui/utils:roles",
        "//cmk/gui/valuespec",
        "//packages/cmk-ccc:plugin-registry",
        requirement("pydantic"),
    ],
)

py_library(
    name = "_snapin",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "_base.py",
            "_permission_section.py",
            "_registry.py",
        ],
    ),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":snapin_registry",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:messaging",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/dashboard",
        "//cmk/gui/monitor/hosts",
        "//cmk/gui/nodevis:topology",
        "//cmk/gui/pagetypes",
        "//cmk/gui/search:matchers",
        "//cmk/gui/search:quicksearch",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:loading_transition",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/views:components",
        "//cmk/gui/visuals",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:groups_io",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)
