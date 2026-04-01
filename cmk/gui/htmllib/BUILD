load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "type_defs",
    srcs = ["type_defs.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "tag_rendering",
    srcs = ["tag_rendering.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":type_defs",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/utils",
    ],
)

py_library(
    name = "generator",
    srcs = ["generator.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":tag_rendering",
        "//cmk/gui:i18n",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:flashed_messages",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//packages/cmk-ccc:exceptions",
    ],
)

py_library(
    name = "debug_vars",
    srcs = ["debug_vars.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":generator",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//packages/cmk-ccc:crash-reporting",
    ],
)

py_library(
    name = "html",
    srcs = [
        "__init__.py",
        "html.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":generator",
        ":tag_rendering",
        ":type_defs",
        "//cmk/gui:ctx_stack",
        "//cmk/gui:dynamic_icon",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:page_menu_entry",
        "//cmk/gui:theme",
        "//cmk/gui:type_defs",
        "//cmk/gui/utils:dataclasses",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:misc",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:popups",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/utils:user_errors",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        requirement("flask"),
    ],
)

py_library(
    name = "foldable_container",
    srcs = ["foldable_container.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":html",
        ":tag_rendering",
        "//cmk/gui:theme",
        "//cmk/gui/utils:html",
    ],
)
