load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "quick_setup",
    srcs = ["__init__.py"] + glob(
        include = [
            "handlers/**/*.py",
            "private/**/*.py",
            "v0_unstable/**/*.py",
        ],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:default_name",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:logged_in",
        "//cmk/gui:permissions",
        "//cmk/gui:site_config",
        "//cmk/gui:user_sites",
        "//cmk/gui/background_job/job",
        "//cmk/gui/fields",
        "//cmk/gui/form_specs",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:roles",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:passwords",
        "//cmk/gui/watolib:registries",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:rulesets",
    ],
)

# Temporary: quick_setup files that still belong to the monolithic //cmk/gui target.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "__init__.py",
            "handlers/**/*.py",
            "private/**/*.py",
            "v0_unstable/**/*.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
