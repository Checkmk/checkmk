load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "form_specs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "generators/host_attributes_selection.py",
            "generators/timeperiod_selection.py",
            "registration.py",
            "visitors/metric.py",
            "visitors/oauth2_connection_setup.py",
            "visitors/password.py",
            "visitors/recomposers/__init__.py",
            "visitors/recomposers/internal_proxy.py",
            "visitors/recomposers/oauth2_connection.py",
            "visitors/recomposers/proxy.py",
            "visitors/recomposers/time_period.py",
            "visitors/single_choice_editable.py",
            "visitors/time_specific.py",
        ],
    ),
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

# Temporary: form_specs files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once the form_specs ↔ watolib cycle is fully resolved.
filegroup(
    name = "gui_srcs",
    srcs = [
        "generators/host_attributes_selection.py",
        "generators/timeperiod_selection.py",
        "registration.py",
        "visitors/metric.py",
        "visitors/oauth2_connection_setup.py",
        "visitors/password.py",
        "visitors/recomposers/__init__.py",
        "visitors/recomposers/internal_proxy.py",
        "visitors/recomposers/oauth2_connection.py",
        "visitors/recomposers/proxy.py",
        "visitors/recomposers/time_period.py",
        "visitors/single_choice_editable.py",
        "visitors/time_specific.py",
    ],
    visibility = ["//cmk/gui:__pkg__"],
)
