load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "shared",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/utils",
        "//cmk/gui/views:components",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//packages/cmk-web/cmk/web/utils",
        requirement("annotated-types"),
        requirement("pydantic"),
    ],
)
