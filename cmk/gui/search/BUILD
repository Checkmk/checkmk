load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "match_items",
    srcs = ["match_items.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/utils:loading_transition",
        "//cmk/gui/utils:roles",
        "//packages/cmk-ccc:plugin-registry",
    ],
)

py_library(
    name = "search",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["match_items.py"],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":match_items",
        "//cmk/gui:config",
        "//cmk/gui:ctx_stack",
        "//cmk/gui:exceptions",
        "//cmk/gui:global_config",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:logged_in",
        "//cmk/gui:main_menu",
        "//cmk/gui:pages",
        "//cmk/gui:permissions",
        "//cmk/gui:session",
        "//cmk/gui:type_defs",
        "//cmk/gui/background_job/job",
        "//cmk/gui/utils:loading_transition",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:urls",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:registries",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:version",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        requirement("pydantic"),
        requirement("redis"),
    ],
)
