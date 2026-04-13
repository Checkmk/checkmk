load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "form_specs",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:hooks",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:logged_in",
        "//cmk/gui:type_defs",
        "//cmk/gui:user_sites",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:encrypter",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:user_errors",
        "//cmk/gui/valuespec",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        requirement("python-dateutil"),
        requirement("werkzeug"),
    ],
)
